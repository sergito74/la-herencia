"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type Tab = { href: string; label: string; exacto?: boolean };

/** Pestañas por sección del menú Producción (12/11/2026): el menú lleva a la sección y estas pestañas a sus pantallas. */
const GRUPOS: Record<"remitos" | "existencias" | "costos", Tab[]> = {
  remitos: [
    { href: "/produccion/remitos", label: "Remitos", exacto: true },
    { href: "/produccion/remitos/facturas-sin-remito", label: "Facturas sin remito" },
  ],
  existencias: [
    { href: "/produccion/stock", label: "Existencias", exacto: true },
    { href: "/produccion/stock/bajas", label: "Bajas de stock" },
    { href: "/produccion/stock/ajustes", label: "Ajustes de inventario" },
    { href: "/produccion/stock/unidades", label: "Unidades de productos" },
  ],
  costos: [
    { href: "/imputacion", label: "Automática", exacto: true },
    { href: "/imputacion/documentos", label: "Por documento" },
    { href: "/produccion/ordenes/resultado-cultivo", label: "Costo por cultivo / campaña" },
    { href: "/produccion/contratistas/sin-orden", label: "Facturas de contratistas sin orden" },
  ],
};

export type GrupoProduccion = keyof typeof GRUPOS;

export function RemitosSubNav({ grupo }: { grupo?: GrupoProduccion }) {
  const pathname = usePathname() ?? "";
  if (!grupo) return null;
  return (
    <nav aria-label="Secciones" className="flex flex-wrap gap-1 border-b border-border">
      {GRUPOS[grupo].map((t) => {
        const activo = t.exacto ? pathname === t.href : pathname.startsWith(t.href);
        return (
          <Link key={t.href} href={t.href} aria-current={activo ? "page" : undefined}
            className={`-mb-px border-b-2 px-4 py-2 text-sm ${
              activo ? "border-agro font-semibold text-ink-primary" : "border-transparent text-ink-secondary hover:text-ink-primary"
            }`}>
            {t.label}
          </Link>
        );
      })}
    </nav>
  );
}
