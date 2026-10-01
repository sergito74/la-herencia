"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { useToast } from "@/components/ui/Toast";
import { formatFecha, formatMoneda } from "@/lib/format";
import { ApiError } from "@/services/apiClient";
import {
  actualizarItems,
  aplicarLote,
  crearLote,
  descartarLote,
  fetchLote,
  fetchLotes,
  revertirLote,
  type ItemLote,
} from "@/services/integridadVinculosApi";

const ACCIONES: Record<ItemLote["accion"], string> = { anular: "Anular", pesificar: "Pesificar", reemplazo: "Reemplazo" };

function etiquetaGrupo(grupo: string): string {
  if (grupo === "reemplazo-ambiguo") return "Reemplazos con varios candidatos (elegir de a uno)";
  const [motivo, certeza] = grupo.split("/");
  const nombres: Record<string, string> = {
    "fecha-incoherente": "Pago muy anterior a la factura",
    "doble-imputacion": "Doble imputación (ya pagada vía tarjeta o cheque)",
    "documento-excedido": "Factura imputada de más",
    "moneda-mezclada": "us$ contra pesos",
  };
  return `${nombres[motivo] ?? motivo} — certeza ${certeza}`;
}

function mensaje(e: unknown): string {
  return e instanceof ApiError ? e.message : "Error inesperado.";
}

export function RevisionLote() {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const lotes = useQuery({ queryKey: ["integridad-lotes"], queryFn: fetchLotes });
  const [grupoAbierto, setGrupoAbierto] = useState<string | null>(null);
  const [pagina, setPagina] = useState(1);
  const actual = lotes.data?.[0];
  const idLote = actual?.idLote;

  const lote = useQuery({
    queryKey: ["integridad-lote", idLote, grupoAbierto, pagina],
    queryFn: () => fetchLote(idLote!, grupoAbierto ?? "__ninguno__", pagina),
    enabled: idLote !== undefined,
  });

  const refrescar = () => {
    qc.invalidateQueries({ queryKey: ["integridad-lotes"] });
    qc.invalidateQueries({ queryKey: ["integridad-lote"] });
    qc.invalidateQueries({ queryKey: ["integridad-control"] });
  };
  const accion = useMutation({
    mutationFn: async (fn: () => Promise<unknown>) => fn(),
    onSuccess: refrescar,
    onError: (e) => showToast(mensaje(e), "danger"),
  });

  if (lotes.isLoading) return <LoadingState />;
  if (lotes.isError) return <ErrorState message="No se pudieron leer los lotes." onRetry={() => lotes.refetch()} />;

  const generar = (
    <SoloLectura>
      <button
        type="button"
        className="rounded-md bg-finance px-3 py-1.5 text-sm text-white disabled:opacity-50"
        disabled={accion.isPending}
        onClick={() => accion.mutate(() => crearLote())}
      >
        {accion.isPending ? "Generando propuesta…" : "Generar propuesta de corrección"}
      </button>
    </SoloLectura>
  );

  if (!actual || actual.estado === "descartado" || actual.estado === "revertido") {
    return (
      <div className="space-y-3">
        <EmptyState message="No hay un lote de corrección abierto." />
        {generar}
      </div>
    );
  }
  if (lote.isLoading || !lote.data) return <LoadingState />;
  const d = lote.data;
  const editable = d.estado === "propuesto";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm">
          Lote <strong>#{d.idLote}</strong> · {d.estado} · propuesto el {formatFecha(d.fechaPropuesta)} por {d.usuario}
          {d.backupArchivo && <span className="text-ink-secondary"> · backup {d.backupArchivo}</span>}
        </p>
        <SoloLectura>
          <div className="flex gap-2">
            {editable && (
              <>
                <button
                  type="button"
                  className="rounded-md border border-border px-3 py-1.5 text-sm"
                  onClick={() => window.confirm("¿Descartar esta propuesta?") && accion.mutate(() => descartarLote(d.idLote))}
                >
                  Descartar
                </button>
                <button
                  type="button"
                  className="rounded-md bg-finance px-3 py-1.5 text-sm text-white disabled:opacity-50"
                  disabled={d.ambiguosSinElegir > 0 || accion.isPending}
                  title={d.ambiguosSinElegir ? `Faltan elegir ${d.ambiguosSinElegir} reemplazos (o destildarlos)` : undefined}
                  onClick={() =>
                    window.confirm("Se tomará un backup de WC y se aplicarán los ítems tildados. ¿Continuar?") &&
                    accion.mutate(async () => {
                      const r = await aplicarLote(d.idLote);
                      showToast(`Lote aplicado: ${r.anuladas} anuladas, ${r.creadas} creadas.`, "success");
                    })
                  }
                >
                  {accion.isPending ? "Aplicando…" : "Aplicar lote"}
                </button>
              </>
            )}
            {d.estado === "aplicado" && (
              <button
                type="button"
                className="rounded-md border border-status-danger px-3 py-1.5 text-sm text-status-danger"
                onClick={() =>
                  window.confirm("Se reactivarán las aplicaciones anuladas por este lote y se anularán las creadas. ¿Revertir?") &&
                  accion.mutate(() => revertirLote(d.idLote))
                }
              >
                Revertir lote
              </button>
            )}
            {d.estado === "aplicado" && generar}
          </div>
        </SoloLectura>
      </div>

      <table className="w-full text-sm">
        <thead className="bg-surface-sunken text-left text-xs text-ink-secondary">
          <tr>
            <th className="px-3 py-2">Incluir</th>
            <th className="px-3 py-2">Grupo</th>
            <th className="px-3 py-2">Acción</th>
            <th className="px-3 py-2 text-right">Ítems</th>
            <th className="px-3 py-2 text-right">Incluidos</th>
            <th className="px-3 py-2 text-right">Importe</th>
          </tr>
        </thead>
        <tbody>
          {d.grupos.map((g) => (
            <tr key={`${g.grupo}-${g.accion}`} className="border-t border-border">
              <td className="px-3 py-1.5">
                <input
                  type="checkbox"
                  disabled={!editable}
                  checked={g.incluidos === g.cantidad}
                  ref={(el) => {
                    if (el) el.indeterminate = g.incluidos > 0 && g.incluidos < g.cantidad;
                  }}
                  onChange={(e) =>
                    accion.mutate(() =>
                      actualizarItems(d.idLote, e.target.checked ? { incluirGrupo: g.grupo } : { excluirGrupo: g.grupo })
                    )
                  }
                />
              </td>
              <td className="px-3 py-1.5">
                <button
                  type="button"
                  className="text-left text-finance underline-offset-2 hover:underline"
                  onClick={() => {
                    setGrupoAbierto(grupoAbierto === g.grupo ? null : g.grupo);
                    setPagina(1);
                  }}
                >
                  {etiquetaGrupo(g.grupo)}
                </button>
              </td>
              <td className="px-3 py-1.5">{ACCIONES[g.accion]}</td>
              <td className="font-data px-3 py-1.5 text-right">{g.cantidad}</td>
              <td className="font-data px-3 py-1.5 text-right">{g.incluidos}</td>
              <td className="font-data px-3 py-1.5 text-right">{formatMoneda(g.importe)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {grupoAbierto && (
        <div className="rounded-md border border-border">
          <p className="bg-surface-sunken px-3 py-2 text-sm font-medium">{etiquetaGrupo(grupoAbierto)}</p>
          <table className="w-full text-sm">
            <tbody>
              {d.items.map((i) => (
                <tr key={i.idItem} className="border-t border-border align-top">
                  <td className="px-3 py-1.5">
                    <input
                      type="checkbox"
                      disabled={!editable}
                      checked={i.incluido}
                      onChange={(e) =>
                        accion.mutate(() =>
                          actualizarItems(d.idLote, e.target.checked ? { incluir: [i.idItem] } : { excluir: [i.idItem] })
                        )
                      }
                    />
                  </td>
                  <td className="px-3 py-1.5">
                    <p>
                      {ACCIONES[i.accion]}
                      {i.idAplicacion && ` aplicación #${i.idAplicacion}`}
                      {i.tipoDocumento && ` · ${i.tipoDocumento} #${i.idDocumento}`}
                      {i.origenMovimiento && ` · ${i.origenMovimiento} #${i.idMovimientoOrigen}`}
                    </p>
                    <p className="text-xs text-ink-secondary">{i.motivo}</p>
                    {i.candidatos && (
                      <div className="mt-1 space-y-0.5">
                        {i.candidatos.map((c, n) => (
                          <label key={n} className="flex items-center gap-2 text-xs">
                            <input
                              type="radio"
                              name={`cand-${i.idItem}`}
                              disabled={!editable}
                              checked={
                                i.elegido &&
                                i.idDocumento === c.idDocumento &&
                                i.idMovimientoOrigen === c.idMovimientoOrigen
                              }
                              onChange={() => accion.mutate(() => actualizarItems(d.idLote, { elegir: [{ idItem: i.idItem, candidato: n }] }))}
                            />
                            {c.tipoDocumento} #{c.idDocumento} · {c.origenMovimiento} #{c.idMovimientoOrigen} ·{" "}
                            {formatFecha(c.fecha)} · libre {formatMoneda(c.libre)}
                          </label>
                        ))}
                      </div>
                    )}
                  </td>
                  <td className="font-data px-3 py-1.5 text-right">{i.importe !== null ? formatMoneda(i.importe) : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex justify-end gap-2 px-3 py-2 text-sm">
            <button type="button" disabled={pagina === 1} onClick={() => setPagina(pagina - 1)} className="disabled:opacity-40">
              ← Anterior
            </button>
            <button type="button" disabled={d.items.length < 100} onClick={() => setPagina(pagina + 1)} className="disabled:opacity-40">
              Siguiente →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
