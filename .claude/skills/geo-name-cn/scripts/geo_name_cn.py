#!/usr/bin/env python3
"""Client and batch helpers for China's National Geographical Names Database."""

from __future__ import annotations

import argparse
import csv
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://dmfw.mca.gov.cn/9095"
ENDPOINTS = {
    "divisions": "/xzqh/getList",
    "search": "/stname/listPub",
    "details": "/stname/detailsPub",
    "same_name_by_code": "/datastatis/GroupCountNameByCode",
    "same_name_by_type": "/datastatis/GroupCountNameByType",
    "same_pinyin_by_code": "/datastatis/GroupCountPinyinByCode",
    "same_pinyin_by_type": "/datastatis/GroupCountPinyinByType",
}
CATEGORY_CODES = {
    "province": "212",
    "prefecture": "213",
    "county": "214",
    "township": "215",
    "autonomous_area": "216",
    "administrative_village": "2161",
    "community": "2162",
}
MATCH_TYPES = {
    "exact": "精确", "精确": "精确", "精确匹配": "精确",
    "fuzzy": "模糊", "模糊": "模糊", "模糊匹配": "模糊",
}


class GeoNameApiError(RuntimeError):
    """Represent an HTTP, JSON, or service-level API failure."""


@dataclass(frozen=True)
class RequestPlan:
    method: str
    url: str
    params: Mapping[str, Any] | None = None
    data: Mapping[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"method": self.method, "url": self.url,
                "params": dict(self.params or {}), "data": dict(self.data or {})}


def build_session(retries: int = 3, backoff: float = 0.8) -> requests.Session:
    retry = Retry(total=retries, connect=retries, read=retries, status=retries,
                  backoff_factor=backoff, status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=frozenset({"GET", "POST"}), respect_retry_after_header=True)
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.headers.update({
        "Accept": "application/json",
        "User-Agent": "geo-name-cn/1.0 (research client; low-rate public API use)",
        "Referer": "https://dmfw.mca.gov.cn/interface.html",
    })
    return session


def normalize_code(code: str | int | None, root_default: bool = False) -> str | None:
    if code is None or str(code).strip() == "":
        return "00" if root_default else None
    value = str(code).strip()
    if not value.isdigit() or len(value) > 12:
        raise ValueError("Administrative codes must contain 1-12 digits.")
    return "00" if set(value) == {"0"} else value


def normalize_match_type(value: str) -> str:
    try:
        return MATCH_TYPES[value.strip()]
    except KeyError as exc:
        raise ValueError("Match type must be exact/fuzzy or 精确/模糊.") from exc


def flatten_division_tree(root: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def visit(node: Mapping[str, Any], parent: str | None, depth: int) -> None:
        code = str(node.get("code", ""))
        rows.append({"code": code, "name": node.get("name"), "level": node.get("level"),
                     "type": node.get("type"), "parent_code": parent, "tree_depth": depth})
        for child in node.get("children") or []:
            visit(child, code or parent, depth + 1)

    for item in root if isinstance(root, list) else [root]:
        if item:
            visit(item, None, 0)
    return rows


class GeoNameClient:
    def __init__(self, base_url: str = BASE_URL, timeout: tuple[float, float] = (5.0, 30.0),
                 min_interval: float = 0.4, session: Any | None = None,
                 dry_run: bool = False) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.min_interval = max(0.0, min_interval)
        self.session = session or build_session()
        self.dry_run = dry_run
        self._last_request = 0.0

    def _plan(self, method: str, endpoint: str, *, params: Mapping[str, Any] | None = None,
              data: Mapping[str, Any] | None = None) -> RequestPlan:
        return RequestPlan(method, self.base_url + endpoint, params=params, data=data)

    def _request(self, plan: RequestPlan) -> Any:
        if self.dry_run:
            return {"_dry_run": plan.as_dict()}
        delay = self.min_interval - (time.monotonic() - self._last_request)
        if delay > 0:
            time.sleep(delay)
        try:
            response = self.session.request(plan.method, plan.url, params=plan.params, data=plan.data,
                                            timeout=self.timeout)
            self._last_request = time.monotonic()
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise GeoNameApiError(f"API request failed: {plan.method} {plan.url}: {exc}") from exc
        if payload is None:
            raise GeoNameApiError("JSON null: check that detail ID and year use the same search snapshot.")
        if isinstance(payload, Mapping) and payload.get("status") not in (None, 200):
            raise GeoNameApiError(f"API status={payload.get('status')}: {payload.get('message')}")
        return payload

    def divisions(self, code: str | int | None = "00", max_level: int = 3,
                  year: int | None = None) -> Any:
        if max_level not in (0, 1, 2, 3):
            raise ValueError("max_level must be 0, 1, 2, or the observed extension 3.")
        normalized = normalize_code(code, root_default=True)
        if normalized == "00" and max_level == 0:
            raise ValueError("The service returns HTTP 500 for root code 00 with maxLevel=0.")
        params: dict[str, Any] = {"code": normalized, "maxLevel": max_level}
        if year is not None:
            params["year"] = int(year)
        return self._request(self._plan("GET", ENDPOINTS["divisions"], params=params))

    def search(self, st_name: str, *, place_type_code: str | None = None,
               year: int | None = None, search_type: str = "fuzzy",
               code: str | int | None = None, page: int = 1, size: int = 100) -> Any:
        normalized_name = str(st_name).strip()
        normalized_code = normalize_code(code)
        normalized_place_type = str(place_type_code).strip() if place_type_code else ""
        if not normalized_name and (not normalized_code or not normalized_place_type):
            raise ValueError(
                "An empty st_name is allowed only with both code and place_type_code."
            )
        if page < 1:
            raise ValueError("page must start at 1.")
        if not 1 <= size <= 1000:
            raise ValueError("size must be 1-1000; prefer 100 for batch work.")
        params: dict[str, Any] = {"stName": normalized_name,
                                  "searchType": normalize_match_type(search_type),
                                  "page": page, "size": size}
        if normalized_place_type:
            params["placeTypeCode"] = normalized_place_type
        if year is not None:
            params["year"] = int(year)
        if normalized_code:
            params["code"] = normalized_code
        return self._request(self._plan("GET", ENDPOINTS["search"], params=params))

    def search_all(self, max_pages: int = 10000, **kwargs: Any) -> dict[str, Any]:
        size = int(kwargs.pop("size", 100))
        records: list[dict[str, Any]] = []
        seen: set[str] = set()
        expected_total = 0
        for page in range(1, max_pages + 1):
            payload = self.search(page=page, size=size, **kwargs)
            if "_dry_run" in payload:
                return payload
            batch = list(payload.get("records") or [])
            expected_total = int(payload.get("total") or 0)
            for record in batch:
                key = str(record.get("id") or record.get("place_code") or
                          json.dumps(record, sort_keys=True))
                if key not in seen:
                    seen.add(key)
                    records.append(record)
            if not batch or len(batch) < size or len(records) >= expected_total:
                break
        else:
            raise GeoNameApiError(f"Pagination exceeded max_pages={max_pages}.")
        return {"total": expected_total, "records": records,
                "_meta": {"unique_records": len(records), "page_size": size}}

    def details(self, record_id: str, *, year: int | None = None) -> Any:
        if not str(record_id).strip():
            raise ValueError("record_id must be non-empty.")
        data: dict[str, Any] = {"id": str(record_id).strip()}
        if year is not None:
            data["year"] = int(year)
        return self._request(self._plan("POST", ENDPOINTS["details"], data=data))

    def statistic(self, operation: str, name: str, *,
                  dist_code: str | int | None = None) -> Any:
        valid = {key for key in ENDPOINTS if key.startswith("same_")}
        if operation not in valid:
            raise ValueError("Unknown statistic operation.")
        if not str(name).strip():
            raise ValueError("name must be non-empty.")
        normalized = normalize_code(dist_code)
        if operation.endswith("by_type") and not normalized:
            raise ValueError("dist_code is required for by-type statistics.")
        params: dict[str, Any] = {"name": str(name).strip()}
        if normalized:
            params["distCode"] = normalized
        return self._request(self._plan("GET", ENDPOINTS[operation], params=params))

    def fetch_three_levels(self, *, year: int | None = None,
                           cross_check_root: bool = True) -> dict[str, Any]:
        root = self.divisions("00", 1, year)
        if "_dry_run" in root:
            return root
        provinces = [row for row in flatten_division_tree(root.get("data")) if row["level"] == 1]
        by_code: dict[str, dict[str, Any]] = {}
        conflicts: list[dict[str, Any]] = []
        duplicate_codes = 0
        for province in provinces:
            payload = self.divisions(province["code"], 2, year)
            for row in flatten_division_tree(payload.get("data")):
                if row["level"] not in (1, 2, 3):
                    continue
                prior = by_code.get(row["code"])
                if prior:
                    duplicate_codes += 1
                    if (prior["name"], prior["level"]) != (row["name"], row["level"]):
                        conflicts.append({"code": row["code"], "first": prior, "second": row})
                else:
                    by_code[row["code"]] = row
        if conflicts:
            raise GeoNameApiError(f"Conflicting division rows: {conflicts[:3]}")
        rows = sorted(by_code.values(), key=lambda item: (int(item["level"]), item["code"]))
        audit: dict[str, Any] = {
            "strategy": "province-list then one maxLevel=2 request per province",
            "province_requests": len(provinces),
            "unique_counts_by_level": {str(level): sum(row["level"] == level for row in rows)
                                       for level in (1, 2, 3)},
            "duplicate_code_count": duplicate_codes,
            "root_cross_check": None,
        }
        if cross_check_root:
            root_deep = self.divisions("00", 3, year)
            root_rows = {row["code"]: row for row in flatten_division_tree(root_deep.get("data"))
                         if row["level"] in (1, 2, 3)}
            audit["root_cross_check"] = {
                "root_unique_count": len(root_rows),
                "province_strategy_unique_count": len(rows),
                "missing_from_root": sorted(set(by_code) - set(root_rows)),
                "missing_from_province_strategy": sorted(set(root_rows) - set(by_code)),
            }
        return {"records": rows, "audit": audit}

    def search_keywords(self, keywords: Sequence[str], *, place_type_code: str,
                        code: str | int, year: int | None = None,
                        size: int = 100) -> dict[str, Any]:
        records: dict[str, dict[str, Any]] = {}
        totals: dict[str, int] = {}
        for keyword in keywords:
            payload = self.search_all(st_name=keyword, place_type_code=place_type_code,
                                      code=code, year=year, search_type="fuzzy", size=size)
            if "_dry_run" in payload:
                return payload
            totals[keyword] = int(payload.get("total") or 0)
            for record in payload["records"]:
                records[str(record.get("id") or record.get("place_code"))] = record
        return {"records": list(records.values()), "keyword_totals": totals}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--min-interval", type=float, default=0.4)
    sub = parser.add_subparsers(dest="command", required=True)
    divisions = sub.add_parser("divisions")
    divisions.add_argument("--code", default="00"); divisions.add_argument("--max-level", type=int, default=3)
    divisions.add_argument("--year", type=int)
    three = sub.add_parser("three-levels")
    three.add_argument("--year", type=int); three.add_argument("--no-root-cross-check", action="store_true")
    three.add_argument("--csv")
    search = sub.add_parser("search")
    search.add_argument("--name", required=True); search.add_argument("--place-type-code")
    search.add_argument("--year", type=int); search.add_argument("--search-type", default="fuzzy")
    search.add_argument("--code"); search.add_argument("--size", type=int, default=100)
    search.add_argument("--all-pages", action="store_true")
    details = sub.add_parser("details")
    details.add_argument("--id", required=True); details.add_argument("--year", type=int)
    stats = sub.add_parser("stats")
    stats.add_argument("--operation", required=True,
                       choices=sorted(key for key in ENDPOINTS if key.startswith("same_")))
    stats.add_argument("--name", required=True); stats.add_argument("--dist-code")
    keywords = sub.add_parser("search-keywords")
    keywords.add_argument("--keywords", nargs="+", required=True)
    keywords.add_argument("--place-type-code", required=True); keywords.add_argument("--code", required=True)
    keywords.add_argument("--year", type=int); keywords.add_argument("--size", type=int, default=100)
    for command in (divisions, three, search, details, stats, keywords):
        command.add_argument("--json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    client = GeoNameClient(args.base_url, min_interval=args.min_interval, dry_run=args.dry_run)
    if args.command == "divisions":
        result = client.divisions(args.code, args.max_level, args.year)
    elif args.command == "three-levels":
        result = client.fetch_three_levels(year=args.year,
                                           cross_check_root=not args.no_root_cross_check)
        if args.csv and "records" in result:
            write_csv(Path(args.csv), result["records"],
                      ("code", "name", "level", "type", "parent_code", "tree_depth"))
    elif args.command == "search":
        kwargs = {"st_name": args.name, "place_type_code": args.place_type_code,
                  "year": args.year, "search_type": args.search_type,
                  "code": args.code, "size": args.size}
        result = client.search_all(**kwargs) if args.all_pages else client.search(**kwargs)
    elif args.command == "details":
        result = client.details(args.id, year=args.year)
    elif args.command == "stats":
        result = client.statistic(args.operation, args.name, dist_code=args.dist_code)
    else:
        result = client.search_keywords(args.keywords, place_type_code=args.place_type_code,
                                        code=args.code, year=args.year, size=args.size)
    if args.json:
        write_json(Path(args.json), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
