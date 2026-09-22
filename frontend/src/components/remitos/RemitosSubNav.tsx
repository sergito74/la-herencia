"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/produccion/planificacion", label: "Planificación agrícola", exacto: true },
  { href: "/produccion/remitos", label: "Remitos", exacto: true },
  { href: "/produccion/remitos/facturas-sin-remito", label: "Facturas sin remito" },
  { href: "/produccion/stock", label: "Existencias", exacto: true },
  { href: "/produccion/stock/bajas", label: "Bajas de stock" },
  { href: "/produccion/stock/ajustes", label: "Ajustes de inventario" },
  { href: "/produccion/stock/unidades", label: "Unidades de productos" },
  { href: "/produccion/ordenes", label: "Órdenes de trabajo", exacto: true },
  { href: "/produccion/resultado-cultivo", label: "Resultado de cultivo", exacto: true },
] as const;

/** Sub-navegación del módulo de insumos: remitos, facturas sin remito y control de stock. */
export function RemitosSubNav() {
  const pathname = usePathname() ?? "";
  return (
    <div className="flex flex-wrap gap-2 border-b border-border pb-2">
      {TABS.map((t) => {
        const activo = "exacto" in t && t.exacto ? pathname === t.href : pathname.startsWith(t.href);
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
