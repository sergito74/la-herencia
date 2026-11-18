import Link from "next/link";

/** Volver atrás (18/11/2026): mismo aspecto que la flecha de PageHeader, con el destino escrito al lado. */
export function BackLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} className="mb-2 inline-flex items-center gap-1.5 rounded-md px-1.5 py-1 text-sm text-ink-secondary hover:bg-surface-sunken hover:text-ink-primary">
      <span aria-hidden>←</span> {children}
    </Link>
  );
}
