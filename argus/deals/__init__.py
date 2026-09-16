"""Private-markets last-mile vertical: CIM intake, thesis scoring, HITL CRM write."""

from argus.deals.catalog import DEAL_CATALOG, resolve_deal
from argus.deals.schemas import DealRecord, FirmThesis, ScoredDeal
from argus.deals.store import DealCloudStore, get_store, reset_store

__all__ = [
    "DEAL_CATALOG",
    "DealCloudStore",
    "DealRecord",
    "FirmThesis",
    "ScoredDeal",
    "get_store",
    "reset_store",
    "resolve_deal",
]
