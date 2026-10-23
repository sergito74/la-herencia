"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

/** Navegación común de "Cajas y socios": resumen, las tres cajas de efectivo y las cuentas de cada socio. */
export const CAJAS_NAV = [
  { href: "/finanzas/cajas", label: "Resumen", grupo: "" },
  { href: "/finanzas/cajas-efectivo/giamigli-sa", label: "Giamigli SA", grupo: "Cajas" },
  { href: "/finanzas/cajas-efectivo/giamigli-dolares", label: "Giamigli US$", grupo: "Cajas" },
  { href: "/finanzas/cajas-efectivo/campo-chica", label: "Caja chica del campo", grupo: "Cajas" },
  { href: "/finanzas/cuentas-socios/1", label: "Sergio", grupo: "Socios" },
  { href: "/finanzas/cuentas-socios/2", label: "Lucy", grupo: "Socios" },
  { href: "/finanzas/cuentas-socios/4", label: "Ceci", grupo: "Socios" },
  { href: "/finanzas/cuentas-socios/3", label: "Condominio LSC", grupo: "Relaciones" },
] as const;

export function CajasNav() {
  const path = usePathname();
  const grupos = ["", "Cajas", "Socios", "Relaciones"] as const;
  const esCondominio = path === "/finanzas/cuentas-socios/3" || path === "/finanzas/cajas-efectivo/condominio-lsc";
  return (
    <><nav aria-label="Cajas y cuentas de socios" className="flex flex-wrap items-center gap-x-5 gap-y-2 rounded-md border border-border bg-surface px-3 py-2">
      {grupos.map((g) => (
        <div key={g || "inicio"} className="flex flex-wrap items-center gap-1">
          {g && <span className="mr-1 text-xs uppercase tracking-wide text-ink-secondary">{g}</span>}
          {CAJAS_NAV.filter((x) => x.grupo === g).map((x) => {
            const activo = path === x.href || (esCondominio && x.href === "/finanzas/cuentas-socios/3");
            return (
              <Link
                key={x.href}
                href={x.href}
                aria-current={activo ? "page" : undefined}
                className={`rounded-sm px-3 py-1 text-sm ${activo ? "bg-agro text-white" : "text-ink-primary hover:bg-surface-sunken"}`}
              >
                {x.label}
              </Link>
            );
          })}
        </div>
      ))}
    </nav>
    {esCondominio && <nav aria-label="Secciones del Condominio LSC" className="mt-3 flex flex-wrap gap-3 text-sm">
      {[{href:"/finanzas/cuentas-socios/3",label:"Cuenta con Giamigli"},{href:"/finanzas/cajas-efectivo/condominio-lsc",label:"Movimientos vinculados"}].map(item => <Link key={item.href} href={item.href} aria-current={path === item.href ? "page" : undefined} className={`rounded border border-border px-3 py-2 ${path === item.href ? "bg-agro text-white" : "bg-surface"}`}>{item.label}</Link>)}
    </nav>}</>
  );
}
