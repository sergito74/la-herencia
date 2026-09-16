"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const TOP_LEVEL_MODULES = [
  { href: "/tesoreria", label: "Tesorería" },
  { href: "/cuentas-corrientes", label: "Cuentas corrientes" },
  { href: "/compras", label: "Compras" },
];

// Nota UX (consulta a 08-agro-erp-frontend-specialist, ver plan.md de
// specs/005-egresos-y-ventas-menores): "Otros movimientos" en vez de
// "Egresos" porque Arrendamientos y Ventas de Hacienda son ingresos, no
// egresos.
const OTROS_MOVIMIENTOS_MODULES = [
  { href: "/impuestos", label: "Impuestos" },
  { href: "/remuneraciones", label: "Remuneraciones" },
  { href: "/arrendamientos", label: "Arrendamientos" },
  { href: "/ventas-hacienda", label: "Ventas de hacienda" },
];

function isActive(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function NavHeader() {
  const pathname = usePathname();
  const [otrosOpen, setOtrosOpen] = useState(false);
  const otrosActive = OTROS_MOVIMIENTOS_MODULES.some((m) => isActive(pathname, m.href));

  return (
    <header className="border-b border-border bg-surface">
      {/* Franja superior: logo + slot reservado para el futuro selector de
          contexto (Establecimiento/Campaña) — design/agroux-frontend-redesign.md §3.1/§3.3.
          No hay datos de Establecimiento/Campaña en SQL Server todavía;
          el botón queda deshabilitado como reserva de layout. */}
      <div className="mx-auto flex max-w-6xl items-center justify-between px-8 py-2">
        <Link href="/" className="font-semibold text-ink-primary">
          La Herencia
        </Link>
        <button
          type="button"
          disabled
          title="Selector de Establecimiento/Campaña — próximamente"
          className="rounded-sm border border-border px-3 py-1 text-xs text-ink-muted disabled:cursor-not-allowed"
        >
          Establecimiento: todos
        </button>
      </div>

      {/* Franja de navegación: jerarquía visual real entre primaria y
          secundaria (design/agroux-frontend-redesign.md §3.1). */}
      <div className="mx-auto flex max-w-6xl items-center gap-1 border-t border-border px-8">
        {TOP_LEVEL_MODULES.map((m) => {
          const active = isActive(pathname, m.href);
          return (
            <Link
              key={m.href}
              href={m.href}
              className={`px-3 py-2.5 text-sm font-medium transition-colors ${
                active
                  ? "border-b-2 border-finance bg-finance-light text-finance"
                  : "border-b-2 border-transparent text-ink-secondary hover:text-ink-primary"
              }`}
            >
              {m.label}
            </Link>
          );
        })}

        <div
          className="relative"
          onMouseEnter={() => setOtrosOpen(true)}
          onMouseLeave={() => setOtrosOpen(false)}
        >
          <button
            type="button"
            className={`px-3 py-2.5 text-sm transition-colors ${
              otrosActive
                ? "border-b-2 border-finance bg-finance-light font-medium text-finance"
                : "border-b-2 border-transparent text-ink-secondary hover:text-ink-primary"
            }`}
            onClick={() => setOtrosOpen((v) => !v)}
            aria-expanded={otrosOpen}
          >
            Otros movimientos ▾
          </button>
          {otrosOpen && (
            <div className="absolute left-0 top-full z-10 min-w-[12rem] rounded-md border border-border bg-surface py-1 shadow-lg">
              {OTROS_MOVIMIENTOS_MODULES.map((m) => {
                const active = isActive(pathname, m.href);
                return (
                  <Link
                    key={m.href}
                    href={m.href}
                    className={`block px-4 py-2 text-sm ${
                      active
                        ? "font-medium text-finance"
                        : "text-ink-secondary hover:bg-surface-sunken hover:text-ink-primary"
                    }`}
                  >
                    {m.label}
                  </Link>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
