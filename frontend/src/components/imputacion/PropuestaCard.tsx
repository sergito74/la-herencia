"use client";

import { useEffect, useState } from "react";

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
  if (f.idCultivo) {
    const cultivo = catalogos?.cultivos.find((c) => c.idCultivo === f.idCultivo)?.nombre ?? `Cultivo ${f.idCultivo}`;
    const campania = catalogos?.campanias.find((c) => c.idCampania === f.idCampania)?.nombre ?? f.idCampania ?? "—";
    return `${cultivo} / ${campania}`;
  }
  if (f.idCentroCosto) return `Centro de Costos ${f.idCentroCosto}`;
  if (f.esGanaderia) return "Ganadería";
  return "En stock sin consumir";
}

export function PropuestaCard({ idDetalleCompra }: { idDetalleCompra: number }) {
  const [fracciones, setFracciones] = useState<PropuestaFraccion[] | null>(null);
  const [trazas, setTrazas] = useState<Traza[] | null>(null);
  const [catalogos, setCatalogos] = useState<Catalogos | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [editando, setEditando] = useState(false);
  const [correcciones, setCorrecciones] = useState<Record<number, { idCultivo?: number; idCampania?: number }>>({});
  const { showToast } = useToast();

  useEffect(() => {
    apiGet<PropuestaFraccion[]>("/api/imputacion/propuestas", { idDetalleCompra }).then(setFracciones);
    apiGet<Traza[]>(`/api/imputacion/propuestas/${idDetalleCompra}/trazabilidad`).then(setTrazas);
    apiGet<Catalogos>("/api/ordenes/catalogos").then(setCatalogos);
  }, [idDetalleCompra]);

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
      const actualizadas = await apiGet<PropuestaFraccion[]>("/api/imputacion/propuestas", { idDetalleCompra });
      setFracciones(actualizadas);
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
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-ink-secondary">
            <th className="pb-2">Destino</th>
            <th className="pb-2">Importe</th>
            <th className="pb-2">Estado</th>
            {editando && <th className="pb-2">Corregir</th>}
          </tr>
        </thead>
        <tbody>
          {fracciones.map((f) => (
            <tr key={f.idPropuesta} className="border-t border-border">
              <td className="py-1">{etiquetaDestino(f, catalogos)}</td>
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

      {pendiente && (
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
      )}

      {trazas && trazas.length > 0 && (
        <details className="mt-3 text-xs text-ink-secondary">
          <summary className="cursor-pointer">Ver trazabilidad</summary>
          <ul className="mt-2 space-y-1">
            {trazas.map((t) => (
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
