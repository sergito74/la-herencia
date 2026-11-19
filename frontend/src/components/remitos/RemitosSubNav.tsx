"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type Tab = { href: string; label: string; exacto?: boolean };

/** Pestañas por sección del menú Producción (12/11/2026): el menú lleva a la sección y estas pestañas a sus pantallas. */
const GRUPOS: Record<"remitos" | "existencias" | "costos", Tab[]> = {
  remitos: [
    { href: "/produccion/remitos", label: "Remitos", exacto: true },
    { href: "/produccion/remitos/facturas-sin-remito", label: "Facturas sin remito" },
    { href: "/produccion/remitos/vinculos-propuestos", label: "Vínculos propuestos" },
  ],
  existencias: [
    { href: "/produccion/stock", label: "Existencias", exacto: true },
    { href: "/produccion/stock/bajas", label: "Bajas de stock" },
    { href: "/produccion/stock/ajustes", label: "Ajustes de inventario" },
    { href: "/produccion/stock/unidades", label: "Unidades de productos" },
    { href: "/produccion/stock/control", label: "Pendientes de carga" },
  ],
  costos: [
    // 18/11/2026: la imputación de compras pasó al menú Compras; acá quedan los costos de los cultivos.
    { href: "/produccion/ordenes/resultado-cultivo", label: "Costo por cultivo" },
    { href: "/produccion/contratistas/sin-orden", label: "Contratistas sin orden" },
  ],
};

export type GrupoProduccion = keyof typeof GRUPOS;

export function RemitosSubNav({ grupo }: { grupo?: GrupoProduccion }) {
  const pathname = usePathname() ?? "";
  if (!grupo) return null;
  return (
    // 19/11/2026 (anatomía de hoja): pestañas compactas en la fila del título (PageHeader `pestanas`), no en una fila propia.
    <nav aria-label="Secciones" className="inline-flex flex-wrap gap-0.5 rounded-lg border border-border bg-surface-sunken/70 p-0.5">
      {GRUPOS[grupo].map((t) => {
        const activo = t.exacto ? pathname === t.href : pathname.startsWith(t.href);
        return (
          <Link key={t.href} href={t.href} aria-current={activo ? "page" : undefined}
            className={`rounded-md px-2 py-0.5 text-[13px] font-medium transition-colors ${
              activo ? "bg-surface text-finance shadow-sm ring-1 ring-border" : "text-ink-secondary hover:bg-surface/70 hover:text-ink-primary"
            }`}>
            {t.label}
          </Link>
        );
      })}
    </nav>
  );
}
