"""
Search OpenAlex for the 9 unmatched references by title.
Get their openalex ID and source URL as identifier.
"""
import requests
import re
import json
import time
import os

# Read email from environment variable for OpenAlex polite pool
# Set via: setx CROSSREF_MAILTO "your@email.com"
MAILTO = os.environ.get("CROSSREF_MAILTO", "")
HEADERS_OA = {"User-Agent": f"mailto:{MAILTO}"} if MAILTO else {}

# The 9 unmatched references with their titles for searching
UNMATCHED = [
    # Barrett
    {
        "paper": "Barrett2022JEL",
        "num": 38,
        "title": "A Revised and Expanded Food Dollar Series: A Better Understanding of Our Food Costs",
        "author": "Canning",
        "year": "2011",
    },
    {
        "paper": "Barrett2022JEL",
        "num": 76,
        "title": "Market Institutions in Sub-Saharan Africa: Theory and Evidence",
        "author": "Fafchamps",
        "year": "2003",
    },
    {
        "paper": "Barrett2022JEL",
        "num": 138,
        "title": "Transformation of the Food System in Nigeria and Female Participation in the Non-farm Sector",
        "author": "Liverpool-Tasie",
        "year": "2016",
    },
    {
        "paper": "Barrett2022JEL",
        "num": 189,
        "title": "The Quiet Revolution in Staple Food Value Chains: Enter the Dragon, the Elephant and the Tiger",
        "author": "Reardon",
        "year": "2012",
    },
    {
        "paper": "Barrett2022JEL",
        "num": 224,
        "title": "Quality Standards, Value Chains, and International Development: Economic and Business Analysis",
        "author": "Swinnen",
        "year": "2015",
    },
    {
        "paper": "Barrett2022JEL",
        "num": 255,
        "title": "Floriculture in Kenya",
        "author": "Whitaker",
        "year": "2006",
    },
    # Tabe-Ojong
    {
        "paper": "Tabe-Ojong2024FPol",
        "num": 7,
        "title": "Who Benefits from State and Local Economic Development Policies",
        "author": "Bartik",
        "year": "1991",
    },
    {
        "paper": "Tabe-Ojong2024FPol",
        "num": 26,
        "title": "Global Agricultural Value Chains and Structural Transformation",
        "author": "Lim",
        "year": "2021",
    },
    # Reardon
    {
        "paper": "Reardon2024FPol",
        "num": 13,
        "title": "Myanmar's Agri-food Systems: Historical Development, Recent Shocks, Future Opportunities",
        "author": "Boughton",
        "year": "2024",
    },
]


def search_openalex_by_title(title):
    """Search OpenAlex for a work by exact title."""
    url = f"https://api.openalex.org/works?search={requests.utils.quote(title)}&per-page=5"
    try:
        resp = requests.get(url, headers=HEADERS_OA, timeout=15)
        if resp.status_code == 200:
            return resp.json().get("results", [])
    except Exception as e:
        print(f"  Error: {e}")
    return []


def find_best_match(title, author, year, results):
    """Find the best matching result."""
    for item in results:
        t = (item.get("title") or "").lower()
        query_t = title.lower()
        # Simple check: does the title contain key words from query?
        query_words = set(query_t.split())
        title_words = set(t.split())
        overlap = len(query_words & title_words) / len(query_words) if query_words else 0
        if overlap > 0.4:
            return item
    return None


if __name__ == "__main__":
    found = 0
    for ref in UNMATCHED:
        print(f"\nSearching: [{ref['paper']} #{ref['num']}] {ref['author']} ({ref['year']})")
        print(f"  Title: {ref['title']}")

        results = search_openalex_by_title(ref["title"])
        match = find_best_match(ref["title"], ref["author"], ref["year"], results)

        if match:
            found += 1
            openalex_id = match.get("id", "")
            openalex_url = match.get("doi") or match.get("primary_location", {}).get("source", {}).get("url") or ""
            source_url = match.get("primary_location", {}).get("source", {}).get("id", "")

            print(f"  FOUND! OpenAlex ID: {openalex_id}")
            print(f"  Title: {match.get('title')}")
            print(f"  DOI: {match.get('doi')}")
            print(f"  Type: {match.get('type')}")
            print(f"  Source: {source_url}")

            # Determine identifier: DOI > source URL
            identifier = match.get("doi")
            identifier_type = "DOI"
            if not identifier:
                # Use the work's own URL as identifier
                identifier = f"https://openalex.org/{openalex_id.split('/')[-1]}"
                identifier_type = "OpenAlex_URL"

            ref["identifier"] = identifier
            ref["identifier_type"] = identifier_type
            ref["openalex_id"] = openalex_id
        else:
            print(f"  NOT FOUND")
            for r in results[:2]:
                print(f"    Candidate: {r.get('title')} (type: {r.get('type')})")

        time.sleep(0.5)

    print(f"\n{'='*50}")
    print(f"Found: {found}/{len(UNMATCHED)}")

    # Save results
    results_data = []
    for ref in UNMATCHED:
        if ref.get("identifier"):
            results_data.append({
                "paper": ref["paper"],
                "num": ref["num"],
                "identifier": ref["identifier"],
                "identifier_type": ref["identifier_type"],
                "openalex_id": ref.get("openalex_id", ""),
                "title": ref["title"],
            })

    with open("Output/scripts/unmatched_openalex_search.json", "w", encoding="utf-8") as f:
        json.dump(results_data, f, indent=2, ensure_ascii=False)

    print(f"\nSaved to Output/scripts/unmatched_openalex_search.json")
    for r in results_data:
        print(f"  {r['paper']} #{r['num']}: {r['identifier_type']} = {r['identifier']}")
