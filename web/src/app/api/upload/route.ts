import { NextResponse } from "next/server";
import { intakeUploaded } from "@/lib/engine";
import { bytesToText, slugDealId } from "@/lib/parse";

export const runtime = "nodejs";

export async function POST(request: Request) {
  const form = await request.formData();
  const file = form.get("file");
  if (!(file instanceof File)) {
    return NextResponse.json({ error: "Choose a .pdf, .txt, or .md file." }, { status: 400 });
  }
  try {
    const bytes = new Uint8Array(await file.arrayBuffer());
    const text = await bytesToText(file.name, bytes, file.type);
    if (text.length < 40) {
      return NextResponse.json(
        { error: "No usable text. If this is a scanned PDF, export text or upload a .txt extract." },
        { status: 422 },
      );
    }
    const dealId = slugDealId(file.name);
    return NextResponse.json(intakeUploaded(text, file.name, dealId));
  } catch (error) {
    const message = error instanceof Error ? error.message : "Could not read that file.";
    return NextResponse.json({ error: message }, { status: 422 });
  }
}
