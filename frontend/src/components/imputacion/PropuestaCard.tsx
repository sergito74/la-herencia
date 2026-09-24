"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ResumenImputacion } from "./ResumenImputacion";
import { EncabezadoPropuesta } from "./EncabezadoPropuesta";
import { SoloLectura } from "@/components/auth/SoloLectura";

import { apiGet, ApiError, apiPost } from "@/services/apiClient";
import { useToast } from "@/components/ui/Toast";
import type { AprobarPropuestaIn, PropuestaFraccion } from "@/services/imputacionApi";

interface Traza {
  idDetalleRemito: number;
  cantidadRemitida: number;
  remito: { idRemito: number; nroRemito: string; fecha: string } | null;
  capaCostoUnitario: number | null;
  capaRestante: number | null;
  consumos: Array<{
    tipoConsumo: string;
    cantidad: number;
    orden?: { idOrdenTrabajo: number; fechaEjecucion: string | null; estado: string } | null;
    baja?: { idBaja: number; motivo: string | null } | null;
  }>;
}

interface Catalogos {
  cultivos: { idCultivo: number; nombre: string }[];
  campanias: { idCampania: number; nombre: string }[];
}

function etiquetaDestino(f: PropuestaFraccion, catalogos: Catalogos | null): string {
  if (f.estado === "RequiereIntervencion") return "Requiere intervención";
  if (f.idCultivo) {
    const cultivo = f.cultivo ?? catalogos?.cultivos.find((c) => c.idCultivo === f.idCultivo)?.nombre ?? "Cultivo sin nombre";
    const campania = f.campania ?? catalogos?.campanias.find((c) => c.idCampania === f.idCampania)?.nombre ?? "Campaña sin nombre";
    return `${cultivo} / ${campania}`;
  }
  if (f.idCentroCosto) return f.centroCosto ?? "Centro de costos sin nombre";
  if (f.esGanaderia) return "Ganadería";
  return "En stock sin consumir";
}

export function PropuestaCard({ idDetalleCompra, onAprobada }: { idDetalleCompra: number; onAprobada?: () => void }) {
  const propuesta = useQuery({
    queryKey: ["imputacion", "detalle", idDetalleCompra],
    queryFn: async () => {
      const todas: PropuestaFraccion[] = [];
      for (let page = 1; ; page++) {
        const parte = await apiGet<PropuestaFraccion[]>("/api/imputacion/propuestas", { idDetalleCompra, page, pageSize: 200 });
        todas.push(...parte);
        if (parte.length < 200) return todas;
      }
    },
  });
  const { data: catalogos = null } = useQuery({
    queryKey: ["ordenes", "catalogos"],
    queryFn: () => apiGet<Catalogos>("/api/ordenes/catalogos"),
  });
  const [verTrazas, setVerTrazas] = useState(false);
  const trazabilidad = useQuery({
    queryKey: ["imputacion", "trazabilidad", idDetalleCompra],
    queryFn: () => apiGet<Traza[]>(`/api/imputacion/propuestas/${idDetalleCompra}/trazabilidad`),
    enabled: verTrazas,
  });
  const trazas = trazabilidad.data;
  const fracciones = propuesta.data;
  const [enviando, setEnviando] = useState(false);
  const [editando, setEditando] = useState(false);
  const [correcciones, setCorrecciones] = useState<Record<number, { idCultivo?: number; idCampania?: number }>>({});
  const { showToast } = useToast();

  if (propuesta.isError) return <p role="alert" className="text-sm text-red-700">No se pudo cargar la propuesta. <button onClick={() => propuesta.refetch()} className="underline">Reintentar</button></p>;
  if (!fracciones) return <p className="text-sm text-ink-secondary">Cargando propuesta…</p>;
  if (fracciones.length === 0) return <p className="text-sm text-ink-secondary">Sin propuesta para este renglón.</p>;

  const idCorrida = fracciones[0].idCorrida;
  const pendiente = fracciones.some((f) => f.estado === "Pendiente");

  async function aprobar() {
    setEnviando(true);
    try {
      const entradas = Object.entries(correcciones);
      const body: AprobarPropuestaIn =
        entradas.length > 0
          ? {
              correcciones: entradas.map(([idPropuesta, c]) => ({
                idPropuesta: Number(idPropuesta),
                idCultivo: c.idCultivo,
                idCampania: c.idCampania,
              })),
            }
          : {};
      await apiPost(`/api/imputacion/propuestas/${idCorrida}/aprobar`, body);
      await propuesta.refetch();
      onAprobada?.();
      setCorrecciones({});
      setEditando(false);
      showToast("Propuesta aprobada.", "success");
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "No se pudo aprobar la propuesta.", "danger");
    } finally {
      setEnviando(false);
    }
  }

  function corregirCampo(idPropuesta: number, campo: "idCultivo" | "idCampania", valor: string) {
    setCorrecciones((prev) => ({
      ...prev,
      [idPropuesta]: { ...prev[idPropuesta], [campo]: valor ? Number(valor) : undefined },
    }));
  }

  return (
    <div className="rounded-md border border-border p-4">
      <EncabezadoPropuesta contexto={fracciones[0]} />
      <ResumenImputacion filas={fracciones.map((f) => ({ ...f, producto: f.producto || "Insumo o servicio sin descripción" }))} />
      <details className="mt-4" open={editando || undefined}>
      <summary className="mb-2 cursor-pointer text-sm font-medium">Detalle de imputación línea a línea</summary>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-ink-secondary">
            <th className="pb-2">Destino</th>
            <th className="pb-2">Cantidad</th>
            <th className="pb-2">Importe (ARS)</th>
            <th className="pb-2">Estado</th>
            {editando && <th className="pb-2">Corregir</th>}
          </tr>
        </thead>
        <tbody>
          {fracciones.map((f) => (
            <tr key={f.idPropuesta} className="border-t border-border">
              <td className="py-1">{etiquetaDestino(f, catalogos)}</td>
              <td className="py-1">{f.origen === "Contratista" ? "No aplica" : f.cantidad == null ? "No registrada" : `${f.cantidad.toLocaleString("es-AR", { maximumFractionDigits: 4 })} ${f.unidad || "(unidad no informada)"}`}</td>
              <td className="py-1">{f.importe.toLocaleString("es-AR")}</td>
              <td className="py-1">
                {f.estado}
                {f.estado === "Aprobada" && f.usuarioAprobacion && (
                  <span className="ml-1 text-xs text-ink-secondary">por {f.usuarioAprobacion}</span>
                )}
              </td>
              {editando && f.estado === "Pendiente" && (
                <td className="py-1">
                  <select
                    className="rounded-sm border border-border px-1 py-0.5 text-xs"
                    defaultValue=""
                    onChange={(e) => corregirCampo(f.idPropuesta, "idCultivo", e.target.value)}
                  >
                    <option value="">Cultivo (sin cambio)</option>
                    {catalogos?.cultivos.map((c) => (
                      <option key={c.idCultivo} value={c.idCultivo}>
                        {c.nombre}
                      </option>
                    ))}
                  </select>
                  <select
                    className="ml-1 rounded-sm border border-border px-1 py-0.5 text-xs"
                    defaultValue=""
                    onChange={(e) => corregirCampo(f.idPropuesta, "idCampania", e.target.value)}
                  >
                    <option value="">Campaña (sin cambio)</option>
                    {catalogos?.campanias.map((c) => (
                      <option key={c.idCampania} value={c.idCampania}>
                        {c.nombre}
                      </option>
                    ))}
                  </select>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
      </details>

      {pendiente && (
        <SoloLectura>
        <div className="mt-3 flex gap-2">
          <button
            type="button"
            onClick={aprobar}
            disabled={enviando}
            className="rounded-md bg-agro px-3 py-1.5 text-sm text-white disabled:opacity-60"
          >
            {enviando ? "Aprobando…" : editando ? "Aprobar con correcciones" : "Aprobar"}
          </button>
          <button
            type="button"
            onClick={() => setEditando((v) => !v)}
            className="rounded-md border border-border px-3 py-1.5 text-sm text-ink-secondary"
          >
            {editando ? "Cancelar corrección" : "Corregir"}
          </button>
        </div>
        </SoloLectura>
      )}

      {fracciones[0].origen === "Insumo" && (
        <details className="mt-3 text-xs text-ink-secondary" onToggle={(e) => setVerTrazas(e.currentTarget.open)}>
          <summary className="cursor-pointer">Ver trazabilidad</summary>
          {trazabilidad.isLoading && <p>Cargando trazabilidad…</p>}
          {trazabilidad.isError && <p role="alert">No se pudo cargar la trazabilidad.</p>}
          {trazas?.length === 0 && <p>Sin trazabilidad disponible.</p>}
          <ul className="mt-2 space-y-1">
            {trazas?.map((t) => (
              <li key={t.idDetalleRemito}>
                Remito {t.remito?.nroRemito ?? "?"} ({t.remito?.fecha ?? "?"}) — costo unitario{" "}
                {t.capaCostoUnitario ?? "—"}
                <ul className="ml-4">
                  {t.consumos.map((c, i) => (
                    <li key={i}>
                      {c.tipoConsumo === "ordenTrabajo"
                        ? `Orden ${c.orden?.idOrdenTrabajo} — ${c.cantidad}`
                        : `Baja ${c.baja?.idBaja} (${c.baja?.motivo ?? "sin motivo"}) — ${c.cantidad}`}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
