import deals from "./deals.json";
import type { DealRecord, FirmThesis } from "./types";

export const ACME_THESIS = deals.thesis as FirmThesis;

export const DEALS = deals.deals as DealRecord[];

export function getDeal(dealId: string): DealRecord {
  const deal = DEALS.find((item) => item.id === dealId);
  if (!deal) {
    throw new Error(`Unknown deal: ${dealId}`);
  }
  return deal;
}

export function listDeals(): DealRecord[] {
  return DEALS;
}
