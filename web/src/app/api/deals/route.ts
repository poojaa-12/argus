import { NextResponse } from "next/server";
import { buildCatalog } from "@/lib/engine";

export async function GET() {
  return NextResponse.json(buildCatalog());
}
