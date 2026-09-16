import { NextResponse } from "next/server";
import { ACME_THESIS, listDeals } from "@/lib/corpus";

export async function GET() {
  return NextResponse.json({
    thesis: ACME_THESIS,
    deals: listDeals().map(({ id, company, document_type, filename }) => ({
      id,
      company,
      document_type,
      filename,
    })),
  });
}
