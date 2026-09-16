from __future__ import annotations

from pathlib import Path
from typing import Any
import json

FIXTURE_PATH = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "deep_research_suite.json"

DOMAINS = [
    "lithium-ion batteries",
    "mRNA vaccines",
    "H3 geospatial indexing",
    "congestion pricing",
    "transformer LLMs",
    "post-quantum cryptography",
    "fusion energy",
    "CBDC payment rails",
    "satellite internet",
    "urban heat islands",
]
ASPECTS = [
    "history",
    "technical mechanism",
    "key risks",
    "regulation",
    "open research problems",
]


def _item(
    index: int,
    query: str,
    subqueries: list[str],
    claims: list[str],
    *,
    needs_clarification: bool = False,
    operator_steps: list[str] | None = None,
    equivalents: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    query_id = f"dr-{index:03d}"
    golden = [{"name": "web_search", "args": {"query": subquery}} for subquery in subqueries]
    for tool_name in operator_steps or []:
        golden.append({"name": tool_name, "args": {"query": query}})
    return {
        "id": query_id,
        "query": query,
        "subqueries": subqueries,
        "source_claims": claims,
        "golden_tools": golden,
        "operator_steps": operator_steps or [],
        "needs_clarification": needs_clarification,
        "allowed_equivalents": equivalents or {"web_search": ["primary_search"], "primary_search": ["web_search"]},
    }


def build_suite() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    index = 0
    for domain in DOMAINS:
        for aspect in ASPECTS:
            index += 1
            if index > 47:
                break
            subqueries = [f"{domain} overview", f"{domain} {aspect}"]
            query = f"Research {domain} with focus on {aspect} and cite primary facts."
            claims = [
                f"{domain} has a documented {aspect} record.",
                f"Primary literature describes {domain} {aspect} in operational terms.",
            ]
            items.append(_item(index, query, subqueries, claims))
        if index > 47:
            break

    items.append(
        _item(
            48,
            "Investigate the unnamed rival dataset and decide which warehouse table to overwrite.",
            ["unnamed rival dataset", "warehouse overwrite policy"],
            ["The rival dataset is unspecified.", "Overwrite requires an explicit table name."],
            needs_clarification=True,
        )
    )
    items.append(
        _item(
            49,
            "Research lithium recycling yields and write the summary into operator_records.",
            ["lithium recycling yields", "operator_records write policy"],
            ["Recycling yield depends on hydrometallurgical recovery.", "operator_records is the approved sink."],
            operator_steps=["db_write"],
        )
    )
    items.append(
        _item(
            50,
            "Research stale cache keys for Argus evals and delete the expired operator record.",
            ["stale cache keys", "expired operator record"],
            ["Expired eval cache keys can be deleted.", "delete_record removes the operator row."],
            operator_steps=["delete_record"],
        )
    )
    return items


def build_corpus(suite: list[dict[str, Any]] | None = None) -> dict[str, str]:
    corpus: dict[str, str] = {}
    for item in suite or build_suite():
        claims = " ".join(item["source_claims"])
        corpus[item["query"]] = claims
        for subquery, claim in zip(item["subqueries"], item["source_claims"] + item["source_claims"]):
            corpus[subquery] = claim
        for claim in item["source_claims"]:
            corpus[claim] = claim
    return corpus


def load_suite(path: Path | None = None) -> list[dict[str, Any]]:
    fixture = path or FIXTURE_PATH
    if fixture.exists():
        return json.loads(fixture.read_text(encoding="utf-8"))
    return build_suite()


def dump_suite(path: Path | None = None) -> Path:
    fixture = path or FIXTURE_PATH
    fixture.parent.mkdir(parents=True, exist_ok=True)
    fixture.write_text(json.dumps(build_suite(), indent=2) + "\n", encoding="utf-8")
    return fixture
