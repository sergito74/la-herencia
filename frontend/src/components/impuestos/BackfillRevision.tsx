"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/components/auth/AuthContext";
import {
  archivoUrl,
  confirmarBackfill,
  crearRespaldo,
  propuestaBackfill,
  validarBackfill,
  type DecisionBackfill,
  type PropuestaBackfill,
  type RevisionBackfill,
} from "@/services/backfillImpuestosApi";
import { formatMoneda } from "@/lib/format";

const pesos = (v: string | number | null | undefined) => formatMoneda(Number(v ?? 0));
type Item = PropuestaBackfill["items"][number];

function decisionInicial(p: Item): DecisionBackfill {
  return {
    medio: p.medio,
    idMovimiento: p.idMovimiento,
    accion: "incluir",
    fuente: p.candidatos.length ? "comprobante" : "generada",
    tipoImpuesto: p.tipoImpuesto ?? { modo: "generico" },
  };
}

/** Backup verificado de WC antes de confirmar (Constitución, Principio II) —
 * se genera desde acá con un botón. */
function RespaldoBackfill({ token, onReady }: { token: string; onReady: (id: string) => void }) {
  const crear = useMutation({ mutationFn: () => crearRespaldo(token), onSuccess: (d) => onReady(d.backupId) });
  return (
    <div className="space-y-2 rounded border border-border p-3 text-sm">
      <p>Antes de confirmar se hace un backup verificado de la base.</p>
      <button
        type="button"
        className="rounded border border-border px-3 py-1.5 hover:bg-surface-sunken disabled:opacity-50"
        disabled={crear.isPending || crear.isSuccess}
        onClick={() => crear.mutate()}
      >
        {crear.isPending ? "Generando backup…" : crear.isSuccess ? "Backup verificado ✓" : "Generar backup verificado"}
      </button>
      {crear.error && <p role="alert" className="text-status-danger">{crear.error.message}</p>}
    </div>
  );
}

export function BackfillRevision({ organismoId }: { organismoId: number }) {
  const { usuario } = useAuth();
  const readOnly = usuario?.rol === "Lectura";
  const cache = useQueryClient();
  const [page, setPage] = useState(1);
  const [decisions, setDecisions] = useState<Record<string, DecisionBackfill>>({});
  const [revision, setRevision] = useState<RevisionBackfill | null>(null);
  const [backup, setBackup] = useState("");
  const [uuid, setUuid] = useState("");

  const q = useQuery({
    queryKey: ["backfill-propuesta", organismoId, page],
    queryFn: () => propuestaBackfill(organismoId, page),
    staleTime: 30000,
    refetchOnWindowFocus: false,
  });
  const d = q.data;
  const faltantes = d?.items.filter((p) => p.estado === "faltante") ?? [];

  const body = () => ({ organismoId, huellaFuente: d?.huellaFuente, decisiones: Object.values(decisions) });
  const validar = useMutation({
    mutationFn: () => validarBackfill(body()),
    onSuccess: (r) => {
      setRevision(r);
      setBackup("");
      setUuid(crypto.randomUUID());
    },
  });
  const confirmar = useMutation({
    mutationFn: () =>
      confirmarBackfill({
        ...body(),
        huellaPropuesta: revision?.huellaPropuesta,
        preparacion: revision?.preparacion,
        backupId: backup,
        idLote: uuid,
      }),
    onSuccess: () => {
      setRevision(null);
      setDecisions({});
      setBackup("");
      cache.invalidateQueries();
    },
  });

  const invalidar = () => {
    setRevision(null);
    setBackup("");
  };
  const change = (key: string, value: DecisionBackfill) => {
    setDecisions({ ...decisions, [key]: value });
    invalidar();
  };
  const quitar = (key: string) => {
    const copy = { ...decisions };
    delete copy[key];
    setDecisions(copy);
    invalidar();
  };
  // Solo los que no dependen de elegir un comprobante a mano.
  const generables = faltantes.filter((p) => !p.candidatos.length);
  const seleccionarGenerables = () => {
    const copy = { ...decisions };
    for (const p of generables) {
      if (Object.keys(copy).length >= 200) break;
      copy[`${p.medio}:${p.idMovimiento}`] ??= decisionInicial(p);
    }
    setDecisions(copy);
    invalidar();
  };

  return (
    <section className="space-y-4 border-t border-border pt-4">
      <h2 className="text-xl font-semibold">Revisar propuesta</h2>
      {q.isLoading && <p>Buscando comprobantes…</p>}
      {q.error && (
        <p role="alert">
          {q.error.message} <button onClick={() => q.refetch()}>Reintentar</button>
        </p>
      )}
      {d && (
        <>
          <p className="text-sm text-ink-secondary">
            Primero los comprobantes reales, después las boletas generadas desde el pago. Seleccionados:{" "}
            {Object.keys(decisions).length}/200.
          </p>
          {!d.coberturaBusqueda && <p role="alert">Búsqueda de comprobantes incompleta. No se puede confirmar todavía.</p>}
          {d.advertencias.map((a) => (
            <p key={a} className="text-sm text-status-warning">{a}</p>
          ))}
          {generables.length > 0 && !readOnly && (
            <button
              type="button"
              className="rounded border border-border px-3 py-1.5 text-sm hover:bg-surface-sunken"
              onClick={seleccionarGenerables}
            >
              Seleccionar las {generables.length} sin comprobante de esta página
            </button>
          )}
          <div className="space-y-3">
            {faltantes.map((p) => {
              const key = `${p.medio}:${p.idMovimiento}`;
              const selected = decisions[key];
              const parcial = Number(p.importeAGenerar) < Number(p.importe);
              return (
                <fieldset className="rounded border border-border p-3" key={key} disabled={readOnly || confirmar.isPending}>
                  <label className="flex flex-wrap items-center gap-2">
                    <input
                      type="checkbox"
                      checked={!!selected}
                      disabled={!selected && Object.keys(decisions).length >= 200}
                      onChange={(e) => (e.target.checked ? change(key, decisionInicial(p)) : quitar(key))}
                    />
                    <span>{p.fecha}</span>
                    <span>·</span>
                    <span>{p.medio} #{p.idMovimiento}</span>
                    <span>·</span>
                    <span>{p.concepto}</span>
                    <span>·</span>
                    <span>Pago {pesos(p.importe)}</span>
                    <strong className="ml-auto">Boleta {pesos(p.importeAGenerar)}</strong>
                  </label>
                  {parcial && (
                    <p className="mt-1 text-xs text-ink-secondary">
                      {pesos(p.importeCubierto)} de este pago ya lo cubren otros documentos; la boleta es solo por la diferencia.
                    </p>
                  )}
                  {selected && (
                    <div className="mt-2 space-y-2 text-sm">
                      <label className="block">
                        Tipo{" "}
                        <select
                          className="border border-border p-1"
                          value={selected.tipoImpuesto?.modo === "existente" ? selected.tipoImpuesto.idTipoImpuesto : 0}
                          onChange={(e) =>
                            change(key, {
                              ...selected,
                              tipoImpuesto: Number(e.target.value)
                                ? { modo: "existente", idTipoImpuesto: Number(e.target.value) }
                                : { modo: "generico" },
                            })
                          }
                        >
                          <option value={0}>Sin identificar (generada desde el pago)</option>
                          {d.tipos.map((t) => (
                            <option key={t.idTipoImpuesto} value={t.idTipoImpuesto}>{t.nombre}</option>
                          ))}
                        </select>
                      </label>
                      {p.candidatos.length ? (
                        <>
                          <label>
                            Comprobante{" "}
                            <select
                              className="border border-border p-1"
                              value={selected.archivoId ?? ""}
                              onChange={(e) => change(key, { ...selected, archivoId: e.target.value, confirmacionDocumento: false })}
                            >
                              <option value="">Elegir después de revisar</option>
                              {p.candidatos.map((f) => (
                                <option key={f.archivoId} value={f.archivoId}>{f.nombre}</option>
                              ))}
                            </select>
                          </label>
                          {selected.archivoId && (
                            <a className="ml-2 text-finance underline" href={archivoUrl(selected.archivoId, organismoId)} target="_blank" rel="noreferrer">
                              Abrir comprobante
                            </a>
                          )}
                          <label className="block">
                            <input
                              type="checkbox"
                              checked={selected.confirmacionDocumento ?? false}
                              onChange={(e) => change(key, { ...selected, confirmacionDocumento: e.target.checked })}
                            />{" "}
                            Revisé el documento y corresponde a este pago
                          </label>
                        </>
                      ) : (
                        <p className="text-ink-secondary">Se generará desde el pago, sin comprobante real.</p>
                      )}
                      <label>
                        Período (opcional){" "}
                        <input
                          className="border border-border p-1"
                          maxLength={255}
                          value={selected.periodoLiquidado ?? ""}
                          onChange={(e) => change(key, { ...selected, periodoLiquidado: e.target.value || undefined })}
                        />
                      </label>
                      <label className="ml-3">
                        Número (opcional){" "}
                        <input
                          className="border border-border p-1"
                          maxLength={255}
                          value={selected.numeroDocumento ?? ""}
                          onChange={(e) => change(key, { ...selected, numeroDocumento: e.target.value || undefined })}
                        />
                      </label>
                    </div>
                  )}
                </fieldset>
              );
            })}
          </div>
          {!faltantes.length && <p>No hay pagos para completar en esta página.</p>}
          <div className="flex gap-4 text-sm">
            <button disabled={page === 1} onClick={() => { setPage(page - 1); invalidar(); }}>Anterior</button>
            <span>Página {page}</span>
            <button disabled={page * d.pageSize >= d.total} onClick={() => { setPage(page + 1); invalidar(); }}>Siguiente</button>
          </div>
          <button
            className="rounded bg-finance px-3 py-2 text-white disabled:opacity-50"
            disabled={readOnly || !Object.keys(decisions).length || !d.coberturaBusqueda || validar.isPending}
            onClick={() => validar.mutate()}
          >
            Validar selección
          </button>
        </>
      )}
      {(validar.error || confirmar.error) && (
        <p role="alert" className="text-status-danger">{validar.error?.message ?? confirmar.error?.message}</p>
      )}
      {revision && (
        <div className="space-y-3 rounded border border-border p-4">
          <p>
            Revisión final: {revision.cantidad} boletas por {pesos(revision.total)}. Saldo proyectado del organismo:{" "}
            {pesos(revision.saldoProyectado)}.
          </p>
          <RespaldoBackfill key={revision.preparacion} token={revision.preparacion} onReady={setBackup} />
          <button
            className="rounded bg-finance px-3 py-2 text-white disabled:opacity-50"
            disabled={!backup || confirmar.isPending || readOnly}
            onClick={() => confirmar.mutate()}
          >
            Confirmar estas {revision.cantidad} boletas
          </button>
        </div>
      )}
      {confirmar.data && (
        <p role="status">
          Lote {confirmar.data.lote.IdLote}: {confirmar.data.lote.Cantidad} boletas cargadas.
        </p>
      )}
    </section>
  );
}
