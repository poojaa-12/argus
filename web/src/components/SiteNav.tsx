import Link from "next/link";

export default function SiteNav({ active }: { active: "desk" | "case-study" }) {
  const item = (href: string, id: "desk" | "case-study", label: string) => (
    <Link
      href={href}
      className={`rounded-full border px-3 py-1 text-xs ${
        active === id
          ? "border-slate-500 bg-[#17243f] text-zinc-100"
          : "border-transparent text-zinc-400 hover:border-slate-600 hover:text-zinc-100"
      }`}
    >
      {label}
    </Link>
  );

  return (
    <nav className="flex flex-wrap gap-2">
      {item("/", "desk", "Deal desk")}
      {item("/case-study", "case-study", "Case study")}
      <a
        className="rounded-full border border-transparent px-3 py-1 text-xs text-zinc-400 hover:border-slate-600 hover:text-zinc-100"
        href="https://github.com/poojaa-12/argus"
        target="_blank"
        rel="noreferrer"
      >
        GitHub
      </a>
    </nav>
  );
}
