from __future__ import annotations

import re

from argus.deals.corpus import get_deal
from argus.deals.schemas import Citation, DealExtraction

_MONEY = r"\$([0-9]+(?:\.[0-9]+)?)\s*million"
_PCT = r"([0-9]+(?:\.[0-9]+)?)%"
_MULT = r"([0-9]+(?:\.[0-9]+)?)x"
_PAGE = r"\[p\.(\d+)\]"


def _search(pattern: str, text: str) -> re.Match[str] | None:
    return re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)


def _float(match: re.Match[str] | None, group: int = 1) -> float | None:
    if match is None:
        return None
    return float(match.group(group))


def _int(match: re.Match[str] | None, group: int = 1) -> int | None:
    if match is None:
        return None
    return int(match.group(group))


def _line_citation(text: str, field: str, needle: str) -> Citation | None:
    for raw in text.splitlines():
        if needle.lower() in raw.lower():
            page_match = re.search(_PAGE, raw)
            page = int(page_match.group(1)) if page_match else 0
            quote = re.sub(r"\s+", " ", raw).strip()
            return Citation(field=field, quote=quote[:180], page=page)
    return None


def _field(label: str, text: str) -> str | None:
    match = _search(rf"^{label}:\s*(.+)$", text) or _search(rf"{label}:\s*(.+)$", text)
    if match is None:
        return None
    value = re.sub(_PAGE, "", match.group(1)).strip()
    return value or None


def extract_cim(deal_id: str) -> DealExtraction:
    deal = get_deal(deal_id)
    text = deal.text
    revenue = _float(_search(rf"Revenue:\s*{_MONEY}", text))
    growth = _float(_search(rf"YoY growth:\s*{_PCT}", text))
    ebitda = _float(_search(rf"Adj\. EBITDA:\s*{_MONEY}", text))
    margin = _float(_search(rf"EBITDA margin:\s*{_PCT}", text))
    leverage = _float(_search(rf"Net debt / EBITDA:\s*{_MULT}", text))
    recurring = _float(_search(rf"Recurring revenue:\s*{_PCT}", text))
    employees = _int(_search(r"Employees:\s*([0-9,]+)", text))
    sector = _field("Sector", text)
    hq = _field("HQ", text)

    risks: list[str] = []
    capture = False
    for line in text.splitlines():
        if line.strip().lower() == "risks":
            capture = True
            continue
        if capture:
            cleaned = re.sub(r"^[-*]\s*", "", re.sub(_PAGE, "", line)).strip()
            if not cleaned:
                if risks:
                    break
                continue
            risks.append(cleaned)

    missing: list[str] = []
    mapping = {
        "revenue_m": revenue,
        "yoy_growth_pct": growth,
        "ebitda_m": ebitda,
        "ebitda_margin_pct": margin,
        "net_debt_ebitda": leverage,
        "recurring_revenue_pct": recurring,
    }
    for name, value in mapping.items():
        if value is None:
            missing.append(name)

    citations: list[Citation] = []
    for field, needle in (
        ("revenue_m", "Revenue:"),
        ("yoy_growth_pct", "YoY growth:"),
        ("ebitda_m", "Adj. EBITDA:"),
        ("net_debt_ebitda", "Net debt / EBITDA:"),
        ("sector", "Sector:"),
        ("headquarters", "HQ:"),
        ("recurring_revenue_pct", "Recurring revenue:"),
    ):
        if mapping.get(field) is None and field not in {"sector", "headquarters"}:
            continue
        cited = _line_citation(text, field, needle)
        if cited:
            citations.append(cited)

    first_body = next(
        (
            line.strip()
            for line in text.splitlines()
            if len(line.strip()) > 40 and not line.startswith("Financials")
        ),
        f"{deal.company} {deal.document_type}",
    )

    return DealExtraction(
        deal_id=deal.id,
        company=deal.company,
        document_type=deal.document_type,
        sector=sector,
        headquarters=hq,
        revenue_m=revenue,
        yoy_growth_pct=growth,
        ebitda_m=ebitda,
        ebitda_margin_pct=margin,
        net_debt_ebitda=leverage,
        recurring_revenue_pct=recurring,
        employees=employees,
        summary=first_body[:240],
        risks=risks,
        citations=citations,
        missing_fields=missing,
    )
