import { NextResponse } from "next/server";
import { resumeDeal } from "@/lib/engine";
import type { ScoredDeal } from "@/lib/types";

export async function POST(request: Request) {
  const body = (await request.json()) as { scored?: ScoredDeal; feedback?: string; filename?: string };
  if (!body.scored || !body.feedback) {
    return NextResponse.json({ error: "scored deal and feedback are required" }, { status: 400 });
  }
  const filename = body.filename || `${body.scored.company.replace(/\s+/g, "_")}.pdf`;
  return NextResponse.json(resumeDeal(body.scored, body.feedback, filename));
}
