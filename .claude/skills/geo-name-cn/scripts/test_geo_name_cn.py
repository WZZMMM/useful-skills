#!/usr/bin/env python3
"""Offline tests for geo_name_cn.py."""

from __future__ import annotations

import argparse
import io
import sys
import unittest
from pathlib import Path
from typing import Any

from geo_name_cn import (CATEGORY_CODES, GeoNameClient, flatten_division_tree,
                         normalize_code, normalize_match_type)


class FakeResponse:
    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> Any:
        return self.payload


class FakeSession:
    def __init__(self, payloads: list[Any]) -> None:
        self.payloads = list(payloads)
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        return FakeResponse(self.payloads.pop(0))


class ClientTests(unittest.TestCase):
    def test_skill_runtime_is_self_contained(self) -> None:
        skill_root = Path(__file__).resolve().parents[1]
        required = [
            skill_root / "SKILL.md",
            skill_root / "README.md",
            skill_root / "requirements.txt",
            skill_root / "references" / "api-reference.md",
            skill_root / "references" / "year-semantics.md",
            skill_root / "scripts" / "geo_name_cn.py",
        ]
        self.assertTrue(all(path.is_file() for path in required))
        runtime_source = (skill_root / "scripts" / "geo_name_cn.py").read_text(encoding="utf-8")
        self.assertNotIn("Output/scripts", runtime_source)
        self.assertNotIn("geo_name_cn_skill_stage", runtime_source)

    def test_normalization_and_categories(self) -> None:
        self.assertEqual(normalize_code("000000"), "00")
        self.assertEqual(normalize_match_type("精确匹配"), "精确")
        self.assertEqual(normalize_match_type("模糊匹配"), "模糊")
        self.assertEqual(CATEGORY_CODES["township"], "215")
        self.assertEqual(CATEGORY_CODES["administrative_village"], "2161")
        self.assertEqual(CATEGORY_CODES["community"], "2162")

    def test_search_rejects_empty_name(self) -> None:
        with self.assertRaises(ValueError):
            GeoNameClient(session=FakeSession([]), min_interval=0).search("")

    def test_search_allows_bounded_empty_category_anchor(self) -> None:
        session = FakeSession([{"total": 0, "records": []}])
        GeoNameClient(session=session, min_interval=0).search(
            "", code="110108", place_type_code="2162"
        )
        self.assertEqual(session.calls[0]["params"]["stName"], "")
        self.assertEqual(session.calls[0]["params"]["code"], "110108")
        self.assertEqual(session.calls[0]["params"]["placeTypeCode"], "2162")

    def test_exact_ui_label_is_normalized_before_request(self) -> None:
        session = FakeSession([{"total": 0, "records": []}])
        GeoNameClient(session=session, min_interval=0).search("东华门", search_type="精确匹配")
        self.assertEqual(session.calls[0]["params"]["searchType"], "精确")

    def test_details_uses_form_post_not_json(self) -> None:
        session = FakeSession([{"id": "abc", "standard_name": "Example"}])
        GeoNameClient(session=session, min_interval=0).details("abc", year=2018)
        call = session.calls[0]
        self.assertEqual(call["method"], "POST")
        self.assertEqual(call["data"], {"id": "abc", "year": 2018})
        self.assertNotIn("json", call)

    def test_search_all_deduplicates_ids(self) -> None:
        session = FakeSession([
            {"total": 3, "records": [{"id": "a"}, {"id": "b"}]},
            {"total": 3, "records": [{"id": "b"}, {"id": "c"}]},
        ])
        result = GeoNameClient(session=session, min_interval=0).search_all(st_name="x", size=2)
        self.assertEqual([row["id"] for row in result["records"]], ["a", "b", "c"])
        self.assertEqual(result["_meta"]["unique_records"], 3)

    def test_flatten_distinguishes_level_from_tree_depth(self) -> None:
        tree = {"code": "00", "level": 0, "children": [
            {"code": "11", "name": "Province", "level": 1, "children": [
                {"code": "1101", "name": "County", "level": 3}
            ]}
        ]}
        rows = flatten_division_tree(tree)
        self.assertEqual(rows[-1]["level"], 3)
        self.assertEqual(rows[-1]["tree_depth"], 2)

    def test_three_level_strategy_queries_each_province(self) -> None:
        root = {"status": 200, "data": {"code": "00", "level": 0, "children": [
            {"code": "110000000000", "name": "P1", "level": 1},
            {"code": "120000000000", "name": "P2", "level": 1},
        ]}}
        p1 = {"status": 200, "data": {"code": "110000000000", "name": "P1", "level": 1,
              "children": [{"code": "110100000000", "name": "C1", "level": 3}]}}
        p2 = {"status": 200, "data": {"code": "120000000000", "name": "P2", "level": 1,
              "children": [{"code": "120100000000", "name": "C2", "level": 3}]}}
        session = FakeSession([root, p1, p2])
        result = GeoNameClient(session=session, min_interval=0).fetch_three_levels(
            cross_check_root=False)
        self.assertEqual(result["audit"]["province_requests"], 2)
        self.assertEqual(result["audit"]["unique_counts_by_level"]["3"], 2)
        self.assertEqual(len(session.calls), 3)

    def test_dry_run_performs_no_network_call(self) -> None:
        session = FakeSession([])
        result = GeoNameClient(session=session, min_interval=0, dry_run=True).search(
            "故宫", code="11", search_type="exact")
        self.assertEqual(result["_dry_run"]["params"]["searchType"], "精确")
        self.assertEqual(session.calls, [])


class Tee(io.TextIOBase):
    def __init__(self, *streams: io.TextIOBase) -> None:
        self.streams = streams

    def write(self, text: str) -> int:
        for stream in self.streams:
            stream.write(text)
            stream.flush()
        return len(text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log")
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ClientTests)
    if args.log:
        path = Path(args.log)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            result = unittest.TextTestRunner(stream=Tee(sys.stdout, handle), verbosity=2).run(suite)
    else:
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
