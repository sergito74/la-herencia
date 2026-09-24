"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { PropuestaCard } from "@/components/imputacion/PropuestaCard";
import { EncabezadoPropuesta } from "@/components/imputacion/EncabezadoPropuesta";
import { useToast } from "@/components/ui/Toast";
import { apiGet, ApiError, apiPost } from "@/services/apiClient";
import type { AprobarLoteOut, PendienteIntervencionOut, PropuestaFraccion } from "@/services/imputacionApi";

const MOTIVO: Record<string, { titulo: string; accion: string }> = {
  sinOrdenVinculada: {
    titulo: "Sin Orden de Trabajo vinculada",
    accion: "Vinculá la factura a la Orden de Trabajo que corresponde (en Órdenes de Trabajo) y volvé a calcular.",
  },
  repartoNoCierra: {
    titulo: "El reparto no cierra contra el total de la factura",
    accion: "Revisá las Órdenes vinculadas a esta factura de contratista — la suma repartida difiere del total por más de lo tolerable.",
  },
  fueraDeCalendarioAgricola: {
    titulo: "Fecha fuera del calendario agrícola de ese cultivo",
    accion: "La Orden de origen tiene una fecha que no encaja con el ciclo real de ese Cultivo/Campaña — revisá esa Orden.",
  },
};

export default function ImputacionPage() {
  const searchParams = useSearchParams();
  const idDetalleCompraFoco = searchParams.get("idDetalleCompra");

  const [fracciones, setFracciones] = useState<PropuestaFraccion[]>([]);
  const [pendientesIntervencion, setPendientesIntervencion] = useState<PendienteIntervencionOut[]>([]);
  const [filtro, setFiltro] = useState<"todas" | "pendiente" | "requiereIntervencion">("todas");
  const [calculando, setCalculando] = useState(false);
  const [ultimoCalculo, setUltimoCalculo] = useState<{ insumosCalculados: number; contratistasCalculados: number } | null>(
    null
  );
  const [seleccionadas, setSeleccionadas] = useState<Set<number>>(new Set());
  const [aprobandoLote, setAprobandoLote] = useState(false);
  const { showToast } = useToast();

  async function calcularPendientes() {
    setCalculando(true);
    try {
      const resultado = await apiPost<{ insumosCalculados: number; contratistasCalculados: number }>(
        "/api/imputacion/calcular-pendientes",
        {}
      );
      setUltimoCalculo(resultado);
      showToast(
        `${resultado.insumosCalculados} facturas de insumo y ${resultado.contratistasCalculados} de contratista procesadas.`,
        "success"
      );
      // Recarga el listado actual con lo recién calculado.
      setFiltro((f) => f);
      apiGet<PropuestaFraccion[]>("/api/imputacion/propuestas", {
        estado: filtro === "todas" ? undefined : "Pendiente",
        pageSize: 200,
      }).then(setFracciones);
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "No se pudo calcular las propuestas pendientes.", "danger");
    } finally {
      setCalculando(false);
    }
  }

  function recargarLista() {
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
  }

  useEffect(() => {
    recargarLista();
    setSeleccionadas(new Set());
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  function toggleSeleccion(idDetalleCompra: number) {
    setSeleccionadas((prev) => {
      const next = new Set(prev);
      if (next.has(idDetalleCompra)) next.delete(idDetalleCompra);
      else next.add(idDetalleCompra);
      return next;
    });
  }

  async function aprobarSeleccionadas() {
    const idCorridas = [...seleccionadas]
      .map((idDetalleCompra) => porFactura.get(idDetalleCompra)?.[0]?.idCorrida)
      .filter((v): v is string => Boolean(v));
    if (idCorridas.length === 0) return;
    setAprobandoLote(true);
    try {
      const resultado = await apiPost<AprobarLoteOut>("/api/imputacion/propuestas/aprobar-lote", { idCorridas });
      showToast(
        `${resultado.aprobadas} propuestas aprobadas${resultado.fallidas > 0 ? `, ${resultado.fallidas} fallaron` : ""}.`,
        resultado.fallidas > 0 ? "danger" : "success"
      );
      setSeleccionadas(new Set());
      recargarLista();
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "No se pudo aprobar el lote seleccionado.", "danger");
    } finally {
      setAprobandoLote(false);
    }
  }

  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <h1 className="text-2xl font-semibold">Imputación automática</h1>
      <p className="mt-1 text-sm text-ink-secondary">
        Propuestas de reparto de costos a Cultivo/Campaña calculadas a partir del consumo real (FIFO/Órdenes de
        Trabajo) — quedan pendientes hasta que las apruebes o corrijas.
      </p>

      <div className="mt-4 flex items-center gap-3">
        <SoloLectura>
          <button
            type="button"
            onClick={calcularPendientes}
            disabled={calculando}
            className="rounded-md bg-agro px-3 py-1.5 text-sm text-white disabled:opacity-60"
          >
            {calculando ? "Calculando…" : "Calcular pendientes"}
          </button>
        </SoloLectura>
        {ultimoCalculo && (
          <span className="text-xs text-ink-secondary">
            {ultimoCalculo.insumosCalculados} facturas de insumo y {ultimoCalculo.contratistasCalculados} de
            contratista procesadas.
          </span>
        )}
      </div>

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
          {pendientesIntervencion.map((p) => {
            const info = MOTIVO[p.motivo];
            return (
              <div key={p.idCorrida} className="rounded-md border border-red-200 bg-red-50 p-3 text-sm">
                <EncabezadoPropuesta contexto={p} />
                <p className="mt-1 text-ink-secondary">{info?.titulo ?? p.motivo}</p>
                {info && <p className="mt-0.5 text-xs text-ink-secondary">→ {info.accion}</p>}
              </div>
            );
          })}
          {pendientesIntervencion.length === 0 && (
            <p className="text-sm text-ink-secondary">No hay casos que requieran intervención manual.</p>
          )}
        </div>
      ) : idDetalleCompraFoco ? (
        <div className="mt-6">
          <PropuestaCard key={idDetalleCompraFoco} idDetalleCompra={Number(idDetalleCompraFoco)} onAprobada={recargarLista} />
          <a href="/imputacion" className="mt-2 inline-block text-xs text-ink-secondary underline">
            ← Ver todas las propuestas
          </a>
        </div>
      ) : (
        <div className="mt-6 space-y-6">
          {seleccionadas.size > 0 && (
            <SoloLectura>
              <div className="flex items-center gap-3 rounded-md border border-agro/40 bg-agro/5 p-2">
                <span className="text-sm text-ink-secondary">{seleccionadas.size} factura(s) seleccionada(s)</span>
                <button
                  type="button"
                  onClick={aprobarSeleccionadas}
                  disabled={aprobandoLote}
                  className="rounded-md bg-agro px-3 py-1.5 text-sm text-white disabled:opacity-60"
                >
                  {aprobandoLote ? "Aprobando…" : "Aprobar seleccionadas"}
                </button>
              </div>
            </SoloLectura>
          )}
          {[...porFactura.keys()].map((idDetalleCompra) => {
            const tienePendientes = porFactura.get(idDetalleCompra)?.some((f) => f.estado === "Pendiente");
            return (
              <div key={idDetalleCompra}>
                <div className="mb-2 flex items-center gap-2">
                  {tienePendientes && (
                    <SoloLectura>
                      <input
                        type="checkbox"
                        checked={seleccionadas.has(idDetalleCompra)}
                        onChange={() => toggleSeleccion(idDetalleCompra)}
                      />
                    </SoloLectura>
                  )}
                  {tienePendientes && <span className="text-xs text-ink-secondary">Seleccionar propuesta para aprobación</span>}
                </div>
                <PropuestaCard idDetalleCompra={idDetalleCompra} onAprobada={recargarLista} />
              </div>
            );
          })}
          {porFactura.size === 0 && <p className="text-sm text-ink-secondary">No hay propuestas para mostrar.</p>}
        </div>
      )}
    </main>
  );
}
