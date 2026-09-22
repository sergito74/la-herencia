"use client";

import Link from "next/link";

import { EmptyState } from "@/components/ui/States";
import { formatMoneda } from "@/lib/format";
import type { DetalleCostoItem } from "@/services/resultadoCultivoApi";

export function DetalleCostosPanel({ costos }: { costos: DetalleCostoItem[] }) {
  if (costos.length === 0) return <EmptyState message="Este cultivo y campaña todavía no tienen costos detallados." />;

  const grupos = new Map<string, DetalleCostoItem[]>();
  for (const item of costos) {
    const clave = `${item.concepto}\u0000${item.rubro ?? ""}`;
    grupos.set(clave, [...(grupos.get(clave) ?? []), item]);
  }

  return (
    <div className="overflow-x-auto rounded border border-border bg-surface">
      <table className="w-full min-w-[760px] border-collapse text-left text-sm">
        <thead className="bg-surface-sunken text-xs uppercase text-ink-secondary">
          <tr><th className="px-3 py-2">Concepto / rubro</th><th className="px-3 py-2 text-right">Pesos</th><th className="px-3 py-2 text-right">Dólares</th><th className="px-3 py-2">Origen</th><th className="px-3 py-2">Referencia</th></tr>
        </thead>
        {[...grupos.entries()].map(([clave, items]) => {
          const [concepto, rubro] = clave.split("\u0000");
          const pesos = items.reduce((total, item) => total + item.montoPesos, 0);
          const dolaresIncompletos = items.some((item) => item.montoDolares === null);
          const dolares = items.reduce((total, item) => total + (item.montoDolares ?? 0), 0);
          return (
            <tbody key={clave} className="border-t border-border">
              <tr className="bg-surface-sunken font-medium">
                <td className="px-3 py-2">{concepto}{rubro ? ` · ${rubro}` : ""} <span className="font-normal text-ink-secondary">({items.length})</span></td>
                <td className="px-3 py-2 text-right font-data">{formatMoneda(pesos)}</td>
                <td className="px-3 py-2 text-right font-data">{formatMoneda(dolares, "Dolares")}{dolaresIncompletos ? " · parcial" : ""}</td>
                <td colSpan={2} className="px-3 py-2 text-ink-secondary">Total del grupo</td>
              </tr>
              {items.map((item, index) => (
                <tr key={`${item.origen}-${item.idCompra ?? item.idOrdenTrabajo ?? index}-${index}`}>
                  <td className="px-3 py-2 pl-6 text-ink-secondary">{item.concepto}{item.rubro ? ` · ${item.rubro}` : ""}</td>
                  <td className="px-3 py-2 text-right font-data">{formatMoneda(item.montoPesos)}</td>
                  <td className="px-3 py-2 text-right font-data">{item.montoDolares === null ? "Sin dato" : formatMoneda(item.montoDolares, "Dolares")}</td>
                  <td className="px-3 py-2">{item.origen === "MaquinariaPropia" ? "Maquinaria propia heredada" : item.origen}</td>
                  <td className="px-3 py-2">
                    {item.origen === "OrdenTrabajo" && item.idOrdenTrabajo ? (
                      <Link className="text-finance underline" href={`/produccion/ordenes/${item.idOrdenTrabajo}`}>Ver orden #{item.idOrdenTrabajo}</Link>
                    ) : item.origen === "Compra" ? (
                      <span>Compra #{item.idCompra ?? "—"}{item.idDetalleCompra ? ` · línea ${item.idDetalleCompra}` : ""}</span>
                    ) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          );
        })}
      </table>
    </div>
  );
}
