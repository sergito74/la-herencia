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
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center gap-6 px-8 py-3">
        <Link href="/" className="font-semibold text-slate-900">
          La Herencia
        </Link>
        <nav className="flex items-center gap-4 text-sm">
          {TOP_LEVEL_MODULES.map((m) => {
            const active = isActive(pathname, m.href);
            return (
              <Link
                key={m.href}
                href={m.href}
                className={
                  active
                    ? "font-medium text-slate-900 underline underline-offset-4"
                    : "text-slate-600 hover:text-slate-900"
                }
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
              className={
                otrosActive
                  ? "font-medium text-slate-900 underline underline-offset-4"
                  : "text-slate-600 hover:text-slate-900"
              }
              onClick={() => setOtrosOpen((v) => !v)}
              aria-expanded={otrosOpen}
            >
              Otros movimientos ▾
            </button>
            {otrosOpen && (
              <div className="absolute left-0 top-full z-10 min-w-[12rem] rounded-md border border-slate-200 bg-white py-1 shadow-lg">
                {OTROS_MOVIMIENTOS_MODULES.map((m) => {
                  const active = isActive(pathname, m.href);
                  return (
                    <Link
                      key={m.href}
                      href={m.href}
                      className={`block px-4 py-2 ${
                        active
                          ? "font-medium text-slate-900"
                          : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                      }`}
                    >
                      {m.label}
                    </Link>
                  );
                })}
              </div>
            )}
          </div>
        </nav>
      </div>
    </header>
  );
}
