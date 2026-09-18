"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/finanzas/tarjetas", label: "Tarjetas" },
  { href: "/finanzas/tarjetas/resumenes", label: "Resúmenes" },
  { href: "/finanzas/tarjetas/compras-en-cuotas", label: "Compras en cuotas" },
] as const;

/** Sub-navegación entre las 3 secciones del módulo Tarjetas — antes solo
 * existía un link de nav global al catálogo, sin ningún camino visible
 * hacia Resúmenes ni Compras en cuotas (feedback 2026-09-21: "no hay un
 * link o botón que permita cargar un nuevo resumen" — el botón existía,
 * nadie podía llegar a la pantalla). */
export function TarjetasSubNav() {
  const pathname = usePathname();

  return (
    <div className="flex gap-2 border-b border-border pb-2">
      {TABS.map((t) => {
        const activo = t.href === "/finanzas/tarjetas" ? pathname === t.href : pathname?.startsWith(t.href);
        return (
          <Link
            key={t.href}
            href={t.href}
            className={`rounded px-3 py-1.5 text-sm ${
              activo ? "bg-finance text-white" : "border border-border text-ink-primary hover:bg-surface-sunken"
            }`}
          >
            {t.label}
          </Link>
        );
      })}
    </div>
  );
}
