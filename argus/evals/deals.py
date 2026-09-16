from __future__ import annotations

from argus.deals.corpus import DEALS
from argus.deals.extract import extract_cim
from argus.deals.score import score_deal


NUMERIC_FIELDS = (
    "revenue_m",
    "yoy_growth_pct",
    "ebitda_m",
    "ebitda_margin_pct",
    "net_debt_ebitda",
    "recurring_revenue_pct",
    "employees",
)
TEXT_FIELDS = ("company", "document_type", "sector", "headquarters")


def _close(left: float | None, right: float | None) -> bool:
    if left is None and right is None:
        return True
    if left is None or right is None:
        return False
    return abs(left - right) < 0.05


def evaluate_deals() -> dict:
    rows: list[dict] = []
    field_hits = 0
    field_total = 0
    invented = 0
    missing_ok = 0
    for deal in DEALS:
        extracted = extract_cim(deal.id)
        gold = deal.gold
        field_results: dict[str, bool] = {}
        for field in TEXT_FIELDS:
            field_total += 1
            ok = getattr(extracted, field) == getattr(gold, field)
            field_results[field] = ok
            field_hits += int(ok)
        for field in NUMERIC_FIELDS:
            field_total += 1
            ok = _close(getattr(extracted, field), getattr(gold, field))
            field_results[field] = ok
            field_hits += int(ok)
        for field in gold.missing_fields:
            if getattr(extracted, field) is not None:
                invented += 1
            else:
                missing_ok += 1
        missing_match = set(extracted.missing_fields) == set(gold.missing_fields)
        scored = score_deal(extracted)
        rows.append(
            {
                "deal_id": deal.id,
                "company": deal.company,
                "score": scored.score,
                "recommendation": scored.recommendation,
                "missing_fields": extracted.missing_fields,
                "field_accuracy": field_results,
                "missing_fields_match": missing_match,
            }
        )
    accuracy = field_hits / field_total if field_total else 0.0
    return {
        "total_deals": len(DEALS),
        "field_accuracy": round(accuracy, 4),
        "field_accuracy_pct": round(accuracy * 100, 1),
        "hallucinated_missing_fields": invented,
        "correctly_left_blank": missing_ok,
        "deals": rows,
    }
