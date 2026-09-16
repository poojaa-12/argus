import DealDesk from "@/components/DealDesk";
import { buildCatalog } from "@/lib/engine";

export default function Home() {
  return <DealDesk initial={buildCatalog()} />;
}
