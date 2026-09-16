from __future__ import annotations

from argus.deals.schemas import Citation, DealExtraction, DealRecord, FirmThesis

ACME_THESIS = FirmThesis(
    firm_id="acme-capital",
    firm_name="Acme Capital",
    mandate=(
        "Control and significant-minority investments in North American B2B software "
        "and data infrastructure. Associates screen every CIM against this thesis before "
        "a DealCloud record is created."
    ),
    sectors=["B2B software", "data infrastructure", "vertical SaaS", "payments infrastructure"],
    geographies=["United States", "Canada"],
    revenue_m_min=25.0,
    revenue_m_max=100.0,
    growth_pct_min=15.0,
    max_net_debt_ebitda=6.0,
    avoid=["project-based services", "heavily cyclical industrials", "majority consumer"],
)


def _gold(
    deal_id: str,
    company: str,
    document_type: str,
    *,
    sector: str | None,
    headquarters: str | None,
    revenue_m: float | None,
    yoy_growth_pct: float | None,
    ebitda_m: float | None,
    ebitda_margin_pct: float | None,
    net_debt_ebitda: float | None,
    recurring_revenue_pct: float | None,
    employees: int | None,
    summary: str,
    risks: list[str],
    citations: list[Citation],
    missing_fields: list[str] | None = None,
) -> DealExtraction:
    return DealExtraction(
        deal_id=deal_id,
        company=company,
        document_type=document_type,  # type: ignore[arg-type]
        sector=sector,
        headquarters=headquarters,
        revenue_m=revenue_m,
        yoy_growth_pct=yoy_growth_pct,
        ebitda_m=ebitda_m,
        ebitda_margin_pct=ebitda_margin_pct,
        net_debt_ebitda=net_debt_ebitda,
        recurring_revenue_pct=recurring_revenue_pct,
        employees=employees,
        summary=summary,
        risks=risks,
        citations=citations,
        missing_fields=missing_fields or [],
    )


NORTHWIND_TEXT = """NORTHWIND ANALYTICS, INC.
Confidential Information Memorandum
Prepared for qualified investors only

Company: Northwind Analytics
Sector: B2B software / data observability
HQ: Austin, TX
Employees: 310

Northwind sells a SaaS platform that traces data pipelines for mid-market manufacturers
and logistics operators. 94% of FY2025 revenue was recurring subscription. [p.9]

Financials (FY2025A)
Revenue: $48.2 million [p.12]
YoY growth: 31% [p.12]
Adj. EBITDA: $11.6 million [p.13]
EBITDA margin: 24% [p.13]
Net debt: $48.7 million [p.18]
Net debt / EBITDA: 4.2x [p.18]
Recurring revenue: 94% [p.9]

Risks
- Customer concentration: top 10 accounts are 38% of ARR [p.22]
- Competitive pressure from hyperscaler observability suites [p.24]
"""

HARBORPAY_TEXT = """HARBORPAY, INC.
Confidential Information Memorandum

Company: HarborPay
Sector: B2B payments infrastructure
HQ: Chicago, IL
Employees: 190

HarborPay provides embedded payouts and reconciliation for vertical SaaS platforms.
Gross payment volume grew faster than revenue as take-rate compressed. [p.7]

Financials (FY2025A)
Revenue: $36.4 million [p.11]
YoY growth: 18% [p.11]
Adj. EBITDA: $6.1 million [p.12]
EBITDA margin: 17% [p.12]
Net debt: $41.5 million [p.19]
Net debt / EBITDA: 6.8x [p.19]
Recurring revenue: 81% [p.8]

Risks
- Sponsor-led recap left leverage above 6x [p.19]
- Take-rate compression vs. larger processors [p.16]
"""

HELIOS_TEXT = """HELIOS SOLAR EPC LLC
Teaser — Project Development Platform

Company: Helios Solar
Sector: project-based solar EPC
HQ: Phoenix, AZ
Employees: 540

Helios builds utility-scale solar sites under fixed-price EPC contracts. Revenue is
recognized on percentage-of-completion and is lumpy by construction cycle. [p.3]

Financials (FY2025A)
Revenue: $72.0 million [p.6]
YoY growth: 12% [p.6]
Adj. EBITDA: $8.4 million [p.7]
EBITDA margin: 12% [p.7]
Net debt: $22.0 million [p.9]
Net debt / EBITDA: 2.6x [p.9]
Recurring revenue: 8% [p.4]

Risks
- Backlog depends on interconnection queue timing [p.11]
- Commodity and labor inflation on fixed-price jobs [p.12]
"""

ATLAS_TEXT = """ATLAS CLINICS GROUP
Confidential Information Memorandum

Company: Atlas Clinics
Sector: multi-site specialty healthcare services
HQ: Nashville, TN
Employees: 820

Atlas operates 41 orthopedic clinics. Same-store growth is solid, but reimbursement
mix and physician recruitment drive the model, not software. [p.5]

Financials (FY2025A)
Revenue: $55.1 million [p.10]
YoY growth: 22% [p.10]
Adj. EBITDA: $9.9 million [p.11]
EBITDA margin: 18% [p.11]
Net debt: $39.6 million [p.15]
Net debt / EBITDA: 4.0x [p.15]
Recurring revenue: 0% [p.6]

Risks
- Payer mix and Medicare rate exposure [p.18]
- Key-man risk in physician partners [p.19]
"""

QUORUM_TEXT = """QUORUM DATA LTD.
Confidential Information Memorandum

Company: Quorum Data
Sector: vertical SaaS / insurance data infrastructure
HQ: Toronto, Canada
Employees: 140

Quorum sells policy and claims data products to P&C carriers in Canada and the
United States on multi-year contracts. [p.4]

Financials (FY2025A)
Revenue: $29.3 million [p.8]
YoY growth: 27% [p.8]
Adj. EBITDA: $7.4 million [p.9]
EBITDA margin: 25% [p.9]
Net debt: $18.1 million [p.14]
Net debt / EBITDA: 2.4x [p.14]
Recurring revenue: 91% [p.5]

Risks
- Cross-border data residency requirements [p.17]
- Carrier procurement cycles can slip a quarter [p.18]
"""

MERIDIAN_TEXT = """MERIDIAN LOGISTICS SOFTWARE
One-page teaser

Company: Meridian Logistics
Sector: B2B software / transportation TMS
HQ: Denver, CO

Early teaser circulated by the sell-side advisor. Full CIM and quality of earnings
are not yet in the data room. Do not invent missing financials.

Financials (limited)
Revenue: $41.0 million [p.1]
Employees: 210

The advisor states growth and EBITDA will be provided in the CIM. No leverage
figures are included in this teaser.

Risks
- Incomplete package; associate must wait for CIM before scoring leverage [p.1]
"""

DEALS: list[DealRecord] = [
    DealRecord(
        id="northwind",
        company="Northwind Analytics",
        document_type="CIM",
        filename="Northwind_Analytics_CIM.pdf",
        text=NORTHWIND_TEXT,
        gold=_gold(
            "northwind",
            "Northwind Analytics",
            "CIM",
            sector="B2B software / data observability",
            headquarters="Austin, TX",
            revenue_m=48.2,
            yoy_growth_pct=31.0,
            ebitda_m=11.6,
            ebitda_margin_pct=24.0,
            net_debt_ebitda=4.2,
            recurring_revenue_pct=94.0,
            employees=310,
            summary="SaaS data-observability platform with 94% recurring revenue.",
            risks=[
                "Customer concentration: top 10 accounts are 38% of ARR",
                "Competitive pressure from hyperscaler observability suites",
            ],
            citations=[
                Citation(field="revenue_m", quote="Revenue: $48.2 million", page=12),
                Citation(field="yoy_growth_pct", quote="YoY growth: 31%", page=12),
                Citation(field="ebitda_m", quote="Adj. EBITDA: $11.6 million", page=13),
                Citation(field="net_debt_ebitda", quote="Net debt / EBITDA: 4.2x", page=18),
            ],
        ),
    ),
    DealRecord(
        id="harborpay",
        company="HarborPay",
        document_type="CIM",
        filename="HarborPay_CIM.pdf",
        text=HARBORPAY_TEXT,
        gold=_gold(
            "harborpay",
            "HarborPay",
            "CIM",
            sector="B2B payments infrastructure",
            headquarters="Chicago, IL",
            revenue_m=36.4,
            yoy_growth_pct=18.0,
            ebitda_m=6.1,
            ebitda_margin_pct=17.0,
            net_debt_ebitda=6.8,
            recurring_revenue_pct=81.0,
            employees=190,
            summary="Embedded payouts platform with leverage above the firm's 6x cap.",
            risks=[
                "Sponsor-led recap left leverage above 6x",
                "Take-rate compression vs. larger processors",
            ],
            citations=[
                Citation(field="revenue_m", quote="Revenue: $36.4 million", page=11),
                Citation(field="net_debt_ebitda", quote="Net debt / EBITDA: 6.8x", page=19),
            ],
        ),
    ),
    DealRecord(
        id="helios",
        company="Helios Solar",
        document_type="teaser",
        filename="Helios_Solar_Teaser.pdf",
        text=HELIOS_TEXT,
        gold=_gold(
            "helios",
            "Helios Solar",
            "teaser",
            sector="project-based solar EPC",
            headquarters="Phoenix, AZ",
            revenue_m=72.0,
            yoy_growth_pct=12.0,
            ebitda_m=8.4,
            ebitda_margin_pct=12.0,
            net_debt_ebitda=2.6,
            recurring_revenue_pct=8.0,
            employees=540,
            summary="Project-based solar EPC with lumpy percentage-of-completion revenue.",
            risks=[
                "Backlog depends on interconnection queue timing",
                "Commodity and labor inflation on fixed-price jobs",
            ],
            citations=[
                Citation(field="sector", quote="Sector: project-based solar EPC", page=0),
                Citation(field="recurring_revenue_pct", quote="Recurring revenue: 8%", page=4),
            ],
        ),
    ),
    DealRecord(
        id="atlas",
        company="Atlas Clinics",
        document_type="CIM",
        filename="Atlas_Clinics_CIM.pdf",
        text=ATLAS_TEXT,
        gold=_gold(
            "atlas",
            "Atlas Clinics",
            "CIM",
            sector="multi-site specialty healthcare services",
            headquarters="Nashville, TN",
            revenue_m=55.1,
            yoy_growth_pct=22.0,
            ebitda_m=9.9,
            ebitda_margin_pct=18.0,
            net_debt_ebitda=4.0,
            recurring_revenue_pct=0.0,
            employees=820,
            summary="Physician-led clinic roll-up; reimbursement model, not software.",
            risks=[
                "Payer mix and Medicare rate exposure",
                "Key-man risk in physician partners",
            ],
            citations=[
                Citation(field="sector", quote="Sector: multi-site specialty healthcare services", page=0),
                Citation(field="revenue_m", quote="Revenue: $55.1 million", page=10),
            ],
        ),
    ),
    DealRecord(
        id="quorum",
        company="Quorum Data",
        document_type="CIM",
        filename="Quorum_Data_CIM.pdf",
        text=QUORUM_TEXT,
        gold=_gold(
            "quorum",
            "Quorum Data",
            "CIM",
            sector="vertical SaaS / insurance data infrastructure",
            headquarters="Toronto, Canada",
            revenue_m=29.3,
            yoy_growth_pct=27.0,
            ebitda_m=7.4,
            ebitda_margin_pct=25.0,
            net_debt_ebitda=2.4,
            recurring_revenue_pct=91.0,
            employees=140,
            summary="Insurance data SaaS with US/Canada coverage and 91% recurring revenue.",
            risks=[
                "Cross-border data residency requirements",
                "Carrier procurement cycles can slip a quarter",
            ],
            citations=[
                Citation(field="revenue_m", quote="Revenue: $29.3 million", page=8),
                Citation(field="headquarters", quote="HQ: Toronto, Canada", page=0),
            ],
        ),
    ),
    DealRecord(
        id="meridian",
        company="Meridian Logistics",
        document_type="teaser",
        filename="Meridian_Logistics_Teaser.pdf",
        text=MERIDIAN_TEXT,
        gold=_gold(
            "meridian",
            "Meridian Logistics",
            "teaser",
            sector="B2B software / transportation TMS",
            headquarters="Denver, CO",
            revenue_m=41.0,
            yoy_growth_pct=None,
            ebitda_m=None,
            ebitda_margin_pct=None,
            net_debt_ebitda=None,
            recurring_revenue_pct=None,
            employees=210,
            summary="Incomplete teaser; growth, EBITDA, and leverage are not in the package.",
            risks=["Incomplete package; associate must wait for CIM before scoring leverage"],
            citations=[Citation(field="revenue_m", quote="Revenue: $41.0 million", page=1)],
            missing_fields=["yoy_growth_pct", "ebitda_m", "ebitda_margin_pct", "net_debt_ebitda", "recurring_revenue_pct"],
        ),
    ),
]


def get_deal(deal_id: str) -> DealRecord:
    for deal in DEALS:
        if deal.id == deal_id:
            return deal
    raise KeyError(deal_id)


def list_deals() -> list[DealRecord]:
    return list(DEALS)
