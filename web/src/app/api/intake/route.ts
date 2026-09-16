import { NextResponse } from "next/server";
import { intakeDeal } from "@/lib/engine";

export async function POST(request: Request) {
  const body = (await request.json()) as { dealId?: string };
  if (!body.dealId) {
    return NextResponse.json({ error: "dealId is required" }, { status: 400 });
  }
  try {
    return NextResponse.json(intakeDeal(body.dealId));
  } catch {
    return NextResponse.json({ error: "deal not found" }, { status: 404 });
  }
}
