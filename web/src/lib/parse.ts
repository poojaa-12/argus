import { extractText, getDocumentProxy } from "unpdf";

const MAX_BYTES = 4_500_000;
const TEXT_EXT = [".txt", ".md", ".text", ".csv"];

export function slugDealId(filename: string): string {
  const slug = filename
    .toLowerCase()
    .replace(/\.[^.]+$/, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 48);
  return `upload-${slug || "package"}`;
}

export async function bytesToText(filename: string, bytes: Uint8Array, mime = ""): Promise<string> {
  if (bytes.byteLength > MAX_BYTES) {
    throw new Error("File is over 4.5MB. Trim the package or upload a text extract.");
  }
  const lower = filename.toLowerCase();
  const isPdf = lower.endsWith(".pdf") || mime.includes("pdf") || (bytes.length > 4 && bytes[0] === 0x25 && bytes[1] === 0x50);
  if (isPdf) {
    const pdf = await getDocumentProxy(bytes);
    const extracted = await extractText(pdf, { mergePages: true });
    const raw = extracted.text;
    const text = Array.isArray(raw) ? raw.join("\n") : String(raw ?? "");
    return text.replace(/\r/g, "").trim();
  }
  if (TEXT_EXT.some((ext) => lower.endsWith(ext)) || mime.startsWith("text/") || mime === "application/json") {
    return new TextDecoder().decode(bytes).replace(/\r/g, "").trim();
  }
  const asText = new TextDecoder("utf-8", { fatal: false }).decode(bytes).replace(/\r/g, "").trim();
  if (asText && !asText.includes("\u0000") && asText.split(/\s+/).length > 12) {
    return asText;
  }
  throw new Error("Use a .pdf, .txt, or .md file with selectable text. Scanned image PDFs will not extract.");
}
