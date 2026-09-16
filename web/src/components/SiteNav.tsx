import Link from "next/link";

export default function SiteNav({ active }: { active: "desk" | "case-study" }) {
  const item = (href: string, id: "desk" | "case-study", label: string) => (
    <Link
      href={href}
      className={`px-1 text-[11px] uppercase tracking-[0.12em] ${
        active === id ? "text-zinc-100" : "text-zinc-500 hover:text-zinc-200"
      }`}
    >
      {label}
    </Link>
  );

  return (
    <nav className="flex items-center gap-3">
      {item("/", "desk", "Desk")}
      {item("/case-study", "case-study", "Notes")}
      <a
        className="px-1 text-[11px] uppercase tracking-[0.12em] text-zinc-500 hover:text-zinc-200"
        href="https://github.com/poojaa-12/argus"
        target="_blank"
        rel="noreferrer"
      >
        Repo
      </a>
    </nav>
  );
}
