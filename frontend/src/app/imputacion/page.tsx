"use client";

import { useEffect, useMemo, useState } from "react";

import { PropuestaCard } from "@/components/imputacion/PropuestaCard";
import { apiGet } from "@/services/apiClient";
import type { PendienteIntervencionOut, PropuestaFraccion } from "@/services/imputacionApi";

const ETIQUETA_MOTIVO: Record<string, string> = {
  sinOrdenVinculada: "Sin Orden de Trabajo vinculada",
  repartoNoCierra: "El reparto no cierra contra el total de la factura",
};

export default function ImputacionPage() {
  const [fracciones, setFracciones] = useState<PropuestaFraccion[]>([]);
  const [pendientesIntervencion, setPendientesIntervencion] = useState<PendienteIntervencionOut[]>([]);
  const [filtro, setFiltro] = useState<"todas" | "pendiente" | "requiereIntervencion">("todas");

  useEffect(() => {
    if (filtro === "requiereIntervencion") {
      apiGet<PendienteIntervencionOut[]>("/api/imputacion/pendientes-intervencion", { pageSize: 200 }).then(
        setPendientesIntervencion
      );
      return;
    }
    apiGet<PropuestaFraccion[]>("/api/imputacion/propuestas", {
      estado: filtro === "todas" ? undefined : "Pendiente",
      pageSize: 200,
    }).then(setFracciones);
  }, [filtro]);

  const porFactura = useMemo(() => {
    const agrupado = new Map<number, PropuestaFraccion[]>();
    for (const f of fracciones) {
      const lista = agrupado.get(f.idDetalleCompra) ?? [];
      lista.push(f);
      agrupado.set(f.idDetalleCompra, lista);
    }
    return agrupado;
  }, [fracciones]);

  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <h1 className="text-2xl font-semibold">Imputación automática</h1>
      <div className="mt-4 flex gap-2">
        {(["todas", "pendiente", "requiereIntervencion"] as const).map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setFiltro(f)}
            className={`rounded-md px-3 py-1.5 text-sm ${
              filtro === f ? "bg-agro text-white" : "border border-border text-ink-secondary"
            }`}
          >
            {f === "todas" ? "Todas" : f === "pendiente" ? "Pendientes" : "Requiere intervención"}
          </button>
        ))}
      </div>

      {filtro === "requiereIntervencion" ? (
        <div className="mt-6 space-y-2">
          {pendientesIntervencion.map((p) => (
            <div key={p.idCorrida} className="rounded-md border border-border p-3 text-sm">
              <span className="font-medium">
                {p.origen === "Contratista" ? "Factura de contratista" : "Factura de insumo"} #{p.idDetalleCompra}
              </span>
              <p className="text-ink-secondary">{ETIQUETA_MOTIVO[p.motivo] ?? p.motivo}</p>
            </div>
          ))}
          {pendientesIntervencion.length === 0 && (
            <p className="text-sm text-ink-secondary">No hay casos que requieran intervención manual.</p>
          )}
        </div>
      ) : (
        <div className="mt-6 space-y-6">
          {[...porFactura.keys()].map((idDetalleCompra) => (
            <div key={idDetalleCompra}>
              <h2 className="mb-2 text-sm font-medium text-ink-secondary">Renglón de factura {idDetalleCompra}</h2>
              <PropuestaCard idDetalleCompra={idDetalleCompra} />
            </div>
          ))}
          {porFactura.size === 0 && <p className="text-sm text-ink-secondary">No hay propuestas para mostrar.</p>}
        </div>
      )}
    </main>
  );
}
