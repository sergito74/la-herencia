import Link from "next/link";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

/**
 * Breadcrumb bajo el header en toda vista de detalle
 * (design/agroux-frontend-redesign.md §3.2).
 */
export function Breadcrumb({ items }: { items: BreadcrumbItem[] }) {
  return (
    <nav aria-label="Breadcrumb" className="mb-4 text-sm text-ink-secondary">
      {items.map((item, i) => (
        <span key={i}>
          {i > 0 && <span className="mx-2 text-ink-muted">/</span>}
          {item.href ? (
            <Link href={item.href} className="hover:text-finance hover:underline">
              {item.label}
            </Link>
          ) : (
            <span className="text-ink-primary">{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
