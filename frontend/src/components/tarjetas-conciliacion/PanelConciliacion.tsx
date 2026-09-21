"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  MOTIVOS_DIFERENCIA,
  MOTIVOS_SIN_DOCUMENTO,
  buscarDocumentos,
  conciliarReparto,
  etiquetaMotivo,
  fetchCandidatosLinea,
  fetchConciliacionPreview,
  marcarSinDocumento,
  proponerReparto,
  quitarEstadoLinea,
  vincularComprasLote,
  type ConciliacionCalculo,
  type DocumentoCandidato,
  type RepartoItem,
} from "@/services/tarjetasResumenesApi";
import { urlDocumentoLocal } from "@/services/comprasApi";
import { ApiError } from "@/services/apiClient";
import { esRutaLocalWindows, urlParaAbrirDocumento } from "@/lib/documentoLocal";
import { formatMoneda, formatMonto, formatPorcentaje } from "@/lib/format";
import { filterInputClass } from "@/components/ui/FilterBar";
import { SideDrawer } from "@/components/ui/SideDrawer";
import { useToast } from "@/components/ui/Toast";
import { MoneyInput } from "@/components/ui/MoneyInput";

const nombreDoc = (d: { tipoDocumento: string | null; numeroDocumento: string | null }) =>
  `${d.tipoDocumento ?? "Documento"} ${d.numeroDocumento ?? ""}`.trim();

const monedaDe = (d: { moneda: string | null }) => (d.moneda === "Dolares" ? "Dolares" : "Pesos");


/** Misma regla del backend: $0,10 en pesos, $1,00 si hay documentos en dólares. */
const toleranciaDe = (docs: { moneda: string | null }[]) => (docs.some((d) => d.moneda === "Dolares") ? 1 : 0.1);

type Dialogo = "diferencia" | "sinDocumento" | null;

function MotivoForm({
  opciones,
  titulo,
  confirmar,
  onConfirm,
  onCancel,
  ocupado,
}: {
  opciones: { value: string; label: string }[];
  titulo: string;
  confirmar: string;
  onConfirm: (motivo: string, detalle: string) => void;
  onCancel: () => void;
  ocupado: boolean;
}) {
  const [motivo, setMotivo] = useState(opciones[0].value);
  const [detalle, setDetalle] = useState("");
  const falta = motivo === "Otro" && !detalle.trim();
  return (
    <div className="mt-2 space-y-2 rounded-sm border border-border bg-surface-sunken p-2">
      <p className="text-xs font-medium">{titulo}</p>
      <select className={`${filterInputClass} w-full px-1.5 py-1 text-xs`} value={motivo} onChange={(e) => setMotivo(e.target.value)}>
        {opciones.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      {motivo === "Otro" && (
        <input
          className={`${filterInputClass} w-full px-1.5 py-1 text-xs`}
          placeholder="Detalle del motivo…"
          value={detalle}
          onChange={(e) => setDetalle(e.target.value)}
        />
      )}
      <div className="flex justify-end gap-1">
        <button type="button" onClick={onCancel} className="rounded-sm border border-border px-2 py-0.5 text-xs text-ink-secondary hover:text-ink-primary">
          Cancelar
        </button>
        <button
          type="button"
          disabled={ocupado || falta}
          onClick={() => onConfirm(motivo, detalle)}
          className="rounded-sm bg-finance px-2 py-0.5 text-xs text-white hover:opacity-90 disabled:opacity-40"
        >
          {ocupado ? "Guardando…" : confirmar}
        </button>
      </div>
    </div>
  );
}

function Resultado({ calculo, importeLinea }: { calculo: ConciliacionCalculo; importeLinea: number }) {
  const total = calculo.imputados.reduce((a, i) => a + i.importeImputado, 0);
  const cierra = calculo.estado === "exacta";
  // Con un desvío grande de tipo de cambio lo más probable es que se eligió otro documento,
  // no que falte una nota de ajuste: la pista solo se muestra si el desvío es razonable.
  const faltaAjuste = calculo.tcImplicito != null && !cierra && Math.abs(calculo.desvioTc ?? 1) <= 0.15;
  return (
    <div className="text-xs">
      <div>
        Total imputado {formatMoneda(total)} · línea {formatMoneda(importeLinea)} ·{" "}
        <span className={cierra ? "font-medium text-status-success" : "font-medium text-status-danger"}>
          {cierra
            ? "cierra"
            : calculo.pagoParcial
              ? `paga una parte del documento (el documento es de ${formatMoneda(importeLinea - calculo.diferencia)})`
              : `diferencia ${formatMoneda(calculo.diferencia)}`}
        </span>
      </div>
      {faltaAjuste && (
        <div className="text-ink-secondary">
          Falta una nota de crédito/débito de ajuste de tipo de cambio por ≈ {formatMoneda(calculo.diferencia)} (tipo de
          cambio implícito {formatMonto(calculo.tcImplicito!)}
          {calculo.tcReferencia != null && ` vs ${formatMonto(calculo.tcReferencia)} del documento`}
          {calculo.desvioTc != null && `, ${formatPorcentaje(calculo.desvioTc, true)}`}).
        </div>
      )}
    </div>
  );
}

/**
 * Panel de conciliación de una línea de consumo (009): a la izquierda la línea,
 * otras líneas pendientes del proveedor y el PDF del resumen; a la derecha la
 * canasta de documentos (del proveedor de la línea y de otros), con sugerencias
 * y las acciones Vincular / Aceptar diferencia / Sin documento. Tildando otras
 * líneas se concilian varias contra varios documentos con un reparto editable.
 */
export function PanelConciliacion({
  idLineaConsumo,
  onClose,
  onChanged,
}: {
  idLineaConsumo: number | null;
  onClose: () => void;
  onChanged: () => void;
}) {
  return (
    <SideDrawer open={idLineaConsumo != null} onClose={onClose} title="Conciliar línea de consumo" maxWidthClass="max-w-6xl">
      {idLineaConsumo != null && <ContenidoPanel key={idLineaConsumo} idLineaConsumo={idLineaConsumo} onClose={onClose} onChanged={onChanged} />}
    </SideDrawer>
  );
}

function ContenidoPanel({
  idLineaConsumo,
  onClose,
  onChanged,
}: {
  idLineaConsumo: number;
  onClose: () => void;
  onChanged: () => void;
}) {
  const { showToast } = useToast();
  const [seleccion, setSeleccion] = useState<number[]>([]);
  const [extras, setExtras] = useState<DocumentoCandidato[]>([]);
  const [lineasExtra, setLineasExtra] = useState<number[]>([]);
  const [verPdf, setVerPdf] = useState(false);
  const [dialogo, setDialogo] = useState<Dialogo>(null);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busqueda, setBusqueda] = useState("");
  const [buscando, setBuscando] = useState(false);
  const [resultados, setResultados] = useState<DocumentoCandidato[] | null>(null);
  const [repartoEdit, setRepartoEdit] = useState<RepartoItem[]>([]);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["linea-candidatos", idLineaConsumo],
    queryFn: () => fetchCandidatosLinea(idLineaConsumo),
    staleTime: 0,
    gcTime: 0,
  });

  const idsOrdenados = useMemo(() => [...seleccion].sort((a, b) => a - b), [seleccion]);
  const modoReparto = lineasExtra.length > 0;

  const { data: preview } = useQuery({
    queryKey: ["linea-conciliacion", idLineaConsumo, idsOrdenados],
    queryFn: () => fetchConciliacionPreview(idLineaConsumo, idsOrdenados),
    enabled: seleccion.length > 0 && !modoReparto,
    staleTime: 0,
  });

  const idsLineasReparto = useMemo(() => [idLineaConsumo, ...lineasExtra].sort((a, b) => a - b), [idLineaConsumo, lineasExtra]);
  const { data: propuesta } = useQuery({
    queryKey: ["linea-reparto", idsLineasReparto, idsOrdenados],
    queryFn: () => proponerReparto(idsLineasReparto, idsOrdenados),
    enabled: modoReparto && seleccion.length > 0,
    staleTime: 0,
  });
  useEffect(() => {
    if (propuesta) setRepartoEdit(propuesta.reparto);
  }, [propuesta]);

  const documentos = useMemo(() => {
    const base = data?.documentos ?? [];
    const ids = new Set(base.map((d) => d.idCompra));
    return [...base, ...extras.filter((d) => !ids.has(d.idCompra))];
  }, [data, extras]);
  const porId = useMemo(() => new Map(documentos.map((d) => [d.idCompra, d])), [documentos]);

  const seleccionados = seleccion.map((id) => porId.get(id)).filter((d): d is DocumentoCandidato => d != null);
  const hayFacturaUsd = seleccionados.some((d) => d.moneda === "Dolares" && !d.ajustaTipoCambio);
  const ajustesSinTildar = documentos.filter((d) => d.ajustaTipoCambio && !seleccion.includes(d.idCompra));

  function alternar(id: number) {
    setError(null);
    setSeleccion((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  function alternarLinea(id: number) {
    setError(null);
    setLineasExtra((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  async function buscar() {
    if (busqueda.trim().length < 2) return;
    setBuscando(true);
    try {
      setResultados(await buscarDocumentos(busqueda.trim()));
    } catch {
      setError("No se pudo buscar documentos.");
    } finally {
      setBuscando(false);
    }
  }

  function agregar(d: DocumentoCandidato) {
    setExtras((prev) => (prev.some((x) => x.idCompra === d.idCompra) ? prev : [...prev, d]));
    setSeleccion((prev) => (prev.includes(d.idCompra) ? prev : [...prev, d.idCompra]));
  }

  async function ejecutar(accion: () => Promise<unknown>, mensajeOk: string) {
    setGuardando(true);
    setError(null);
    try {
      await accion();
      showToast(mensajeOk, "success");
      onChanged();
      onClose();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo guardar la conciliación.");
    } finally {
      setGuardando(false);
    }
  }

  if (isLoading) return <p className="text-sm text-ink-secondary">Cargando…</p>;
  if (isError || !data) {
    return (
      <p className="text-sm text-status-danger">
        No se pudo cargar la línea.{" "}
        <button type="button" className="underline" onClick={() => refetch()}>
          Reintentar
        </button>
      </p>
    );
  }

  const { linea, estado } = data;
  const urlPdf = linea.urlResumenOriginal ? urlParaAbrirDocumento(linea.urlResumenOriginal, "", urlDocumentoLocal) : null;
  const compraParams = new URLSearchParams({
    ...(linea.idContacto ? { idContacto: String(linea.idContacto) } : {}),
    ...(linea.proveedor ? { proveedor: linea.proveedor } : {}),
    ...(linea.fechaCompra ? { fecha: linea.fechaCompra.slice(0, 10) } : {}),
    ...(linea.nroDocumento ? { numeroDocumento: linea.nroDocumento } : {}),
    ...(linea.detalle ? { detalle: linea.detalle } : {}),
    importe: String(linea.importe),
  });

  // --- Estado ya resuelto (sin documento / diferencia aceptada) ---
  const resuelto = estado != null;

  // --- Reparto (varias líneas) ---
  const lineasReparto = propuesta?.lineas ?? [];
  const diferenciasReparto = lineasReparto.map((l) => {
    const items = repartoEdit.filter((r) => r.idLinea === l.idLinea);
    const asignado = items.reduce((a, i) => a + i.importe, 0);
    const docs = items.map((i) => porId.get(i.idCompra) ?? propuesta?.documentos.find((d) => d.idCompra === i.idCompra)).filter(Boolean) as DocumentoCandidato[];
    const diferencia = Math.round((l.importe - asignado) * 100) / 100;
    return { idLinea: l.idLinea, importe: l.importe, diferencia, cierra: Math.abs(diferencia) <= toleranciaDe(docs) };
  });
  const repartoNoCierra = diferenciasReparto.some((d) => !d.cierra);

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
      {/* ---------------- Izquierda: línea, hermanas, PDF ---------------- */}
      <section className="space-y-3">
        <div className="rounded-md border border-border bg-surface p-3">
          <div className="text-xs text-ink-secondary">
            {linea.tarjeta ?? "Tarjeta"} · resumen {linea.resumenCodigo ?? linea.idResumen} ·{" "}
            <Link href={`/finanzas/tarjetas/resumenes/${linea.idResumen}`} className="text-finance underline">
              ver resumen
            </Link>
          </div>
          <div className="mt-1 text-sm font-medium">{linea.proveedor ?? "Sin proveedor"}</div>
          <div className="text-xs text-ink-secondary">
            {linea.fechaCompra?.slice(0, 10) ?? "—"} · {linea.detalle ?? "—"}
            {linea.nroDocumento && ` · doc. ${linea.nroDocumento}`}
          </div>
          <div className="mt-2 font-data text-xl font-semibold">{formatMoneda(linea.importe)}</div>
        </div>

        {resuelto && estado && (
          <div className="rounded-md border border-border bg-surface-sunken p-3 text-xs">
            <div className="font-medium">
              {estado.estado === "SinDocumento" ? "Marcada sin documento" : "Diferencia aceptada"} — {etiquetaMotivo(estado.motivo)}
            </div>
            {estado.detalle && <div className="text-ink-secondary">{estado.detalle}</div>}
            {estado.importeDiferencia != null && <div className="text-ink-secondary">Diferencia: {formatMoneda(estado.importeDiferencia)}</div>}
            <button
              type="button"
              className="mt-1 text-finance underline"
              onClick={() => ejecutar(() => quitarEstadoLinea(idLineaConsumo), "Estado quitado.")}
            >
              Volver a pendiente
            </button>
          </div>
        )}

        {data.hermanas.length > 0 && !resuelto && (
          <div className="rounded-md border border-border bg-surface p-3">
            <p className="text-xs font-medium text-ink-secondary">
              Otras líneas pendientes de este proveedor — tildá las que se concilian junto con esta
            </p>
            <ul className="mt-1 max-h-48 space-y-0.5 overflow-auto text-xs">
              {data.hermanas.map((h) => (
                <li key={h.idLineaConsumo}>
                  <label className="flex cursor-pointer items-center gap-2 py-0.5">
                    <input type="checkbox" checked={lineasExtra.includes(h.idLineaConsumo)} onChange={() => alternarLinea(h.idLineaConsumo)} />
                    <span className="flex-1">
                      {h.fechaCompra?.slice(0, 10)} · res. {h.resumenCodigo} · {h.detalle}
                    </span>
                    <span className="font-data">{formatMoneda(h.importe)}</span>
                  </label>
                </li>
              ))}
            </ul>
          </div>
        )}

        {urlPdf && (
          <div className="rounded-md border border-border bg-surface p-3">
            <div className="flex items-center justify-between text-xs">
              <button type="button" className="text-finance underline" onClick={() => setVerPdf((v) => !v)}>
                {verPdf ? "Ocultar PDF del resumen" : "Ver PDF del resumen"}
              </button>
              <a href={urlPdf} target="_blank" rel="noreferrer" className="text-ink-secondary underline">
                Abrir en otra pestaña
              </a>
            </div>
            {verPdf && (
              <iframe
                src={urlPdf}
                title="PDF del resumen"
                className="mt-2 h-[28rem] w-full rounded-sm border border-border"
              />
            )}
            {verPdf && !esRutaLocalWindows(linea.urlResumenOriginal ?? "", "") && (
              <p className="mt-1 text-xs text-ink-secondary">Si el visor queda en blanco, el sitio no permite incrustarlo: usá «Abrir en otra pestaña».</p>
            )}
          </div>
        )}
      </section>

      {/* ---------------- Derecha: canasta de documentos ---------------- */}
      <section className="space-y-3">
        {!resuelto && data.sugerencias.length > 0 && (
          <div>
            <p className="text-xs font-medium text-ink-secondary">Combinaciones que cierran exacto con {formatMoneda(linea.importe)}</p>
            <ul className="mt-1 space-y-1">
              {data.sugerencias.map((s) => (
                <li key={s.idsCompra.join("-")} className="flex flex-wrap items-center justify-between gap-2 rounded-sm bg-surface-sunken px-2 py-1">
                  <span className="text-xs">
                    {s.idsCompra.map((id, i) => {
                      const d = porId.get(id);
                      return (
                        <span key={id}>
                          {i > 0 && <span className="text-ink-secondary"> + </span>}
                          {d ? `${nombreDoc(d)} (${formatMoneda(d.importeOriginal, monedaDe(d))})` : `#${id}`}
                        </span>
                      );
                    })}
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      setLineasExtra([]);
                      setSeleccion(s.idsCompra);
                      setError(null);
                    }}
                    className="rounded-sm border border-finance px-2 py-0.5 text-xs text-finance hover:bg-finance-light"
                  >
                    Usar
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {!resuelto && (
          <div>
            <p className="text-xs font-medium text-ink-secondary">
              {data.idContacto == null
                ? "Esta línea no tiene proveedor asociado: buscá los documentos abajo."
                : `Documentos de ${linea.proveedor ?? "el proveedor"} — tildá uno o más`}
            </p>
            {documentos.length > 0 && (
              <div className="mt-1 max-h-72 overflow-auto rounded-sm border border-border">
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-surface text-left text-ink-secondary">
                    <tr>
                      <th className="w-6" />
                      <th className="py-0.5 pr-2">Fecha</th>
                      <th className="pr-2">Documento</th>
                      <th className="pr-2 text-right">Importe original</th>
                      <th className="pr-2 text-right">TC</th>
                      <th className="pr-1 text-right">Importe en $</th>
                    </tr>
                  </thead>
                  <tbody>
                    {documentos.map((d) => (
                      <tr
                        key={d.idCompra}
                        onClick={() => alternar(d.idCompra)}
                        className={`cursor-pointer border-t border-border hover:bg-surface-sunken ${seleccion.includes(d.idCompra) ? "bg-finance-light" : ""}`}
                      >
                        <td className="py-0.5 pl-1">
                          <input
                            type="checkbox"
                            checked={seleccion.includes(d.idCompra)}
                            onChange={() => alternar(d.idCompra)}
                            onClick={(e) => e.stopPropagation()}
                            aria-label={`Elegir ${nombreDoc(d)}`}
                          />
                        </td>
                        <td className="py-0.5 pr-2 whitespace-nowrap">{d.fecha?.slice(0, 10) ?? "—"}</td>
                        <td className="pr-2">
                          {nombreDoc(d)}
                          {d.ajustaTipoCambio && (
                            <span className="ml-1 rounded-sm bg-finance-light px-1 text-finance" title="Nota que ajusta el tipo de cambio de una factura en dólares">
                              Ajuste TC
                            </span>
                          )}
                          {d.compraParticular < 0 && (
                            <span
                              className="ml-1 rounded-sm bg-surface-sunken px-1 text-ink-secondary"
                              title={`Compra particular: la factura descuenta ${formatMoneda(-d.compraParticular)} y queda en $ 0 neto. Se muestra el importe bruto, que es lo que cobró la tarjeta.`}
                            >
                              Compra particular
                            </span>
                          )}
                          {d.proveedor && d.proveedor !== linea.proveedor && <span className="ml-1 text-ink-secondary">· {d.proveedor}</span>}
                          {d.vinculosPrevios > 0 && (
                            <span className="ml-1 text-ink-secondary" title="Ya está vinculado a otras líneas (ej. cuotas)">
                              · en {d.vinculosPrevios} línea{d.vinculosPrevios > 1 ? "s" : ""}
                            </span>
                          )}
                        </td>
                        <td className="pr-2 text-right font-data whitespace-nowrap">{formatMoneda(d.importeOriginal, monedaDe(d))}</td>
                        <td className="pr-2 text-right font-data">{d.moneda === "Dolares" && d.tipoDeCambio ? formatMonto(d.tipoDeCambio) : "—"}</td>
                        <td className="pr-1 text-right font-data whitespace-nowrap">{formatMoneda(d.importePesos)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {hayFacturaUsd && ajustesSinTildar.length > 0 && (
              <p className="mt-1 text-xs text-ink-secondary">
                Hay una factura en dólares: este proveedor tiene {ajustesSinTildar.length} nota
                {ajustesSinTildar.length > 1 ? "s" : ""} de ajuste de tipo de cambio ({ajustesSinTildar.length > 1 ? "marcadas" : "marcada"} «Ajuste TC»). Tildá la que corresponda.
              </p>
            )}

            <div className="mt-2 rounded-sm border border-dashed border-border p-2">
              <p className="text-xs font-medium text-ink-secondary">Sumar documentos de otro proveedor</p>
              <div className="mt-1 flex gap-1">
                <input
                  className={`${filterInputClass} min-w-0 flex-1 px-1.5 py-0.5 text-xs`}
                  placeholder="Proveedor o número de documento…"
                  value={busqueda}
                  onChange={(e) => setBusqueda(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), buscar())}
                />
                <button type="button" onClick={buscar} disabled={buscando} className="rounded-sm border border-border px-2 py-0.5 text-xs text-ink-secondary hover:text-ink-primary">
                  {buscando ? "Buscando…" : "Buscar"}
                </button>
              </div>
              {resultados && (
                <div className="mt-1 max-h-40 overflow-auto">
                  {resultados.length === 0 && <p className="text-xs text-ink-secondary">Sin resultados.</p>}
                  {resultados.map((d) => (
                    <div key={d.idCompra} className="flex items-center justify-between gap-2 border-t border-border py-0.5 text-xs">
                      <span>
                        {d.proveedor} · {nombreDoc(d)} ({d.fecha?.slice(0, 10)}) · {formatMoneda(d.importeOriginal, monedaDe(d))}
                        {d.ajustaTipoCambio && <span className="ml-1 rounded-sm bg-finance-light px-1 text-finance">Ajuste TC</span>}
                      </span>
                      <button
                        type="button"
                        disabled={seleccion.includes(d.idCompra)}
                        onClick={() => agregar(d)}
                        className="rounded-sm border border-finance px-2 py-0.5 text-finance hover:bg-finance-light disabled:opacity-40"
                      >
                        {seleccion.includes(d.idCompra) ? "Agregado" : "Agregar"}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ---------- Resumen y acciones ---------- */}
        {!resuelto && (
          <div className="rounded-md border border-border bg-surface p-3">
            {!modoReparto && seleccion.length > 0 && preview && (
              <>
                <Resultado calculo={preview} importeLinea={linea.importe} />
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  {(preview.estado === "exacta" || preview.pagoParcial) && (
                    <button
                      type="button"
                      disabled={guardando}
                      onClick={() => ejecutar(() => vincularComprasLote(idLineaConsumo, idsOrdenados), "Documentos vinculados.")}
                      className="rounded-sm bg-finance px-3 py-1 text-xs text-white hover:opacity-90 disabled:opacity-40"
                    >
                      {preview.pagoParcial ? "Vincular como pago parcial" : `Vincular ${seleccion.length}`}
                    </button>
                  )}
                  {preview.estado === "parcial" && !preview.pagoParcial && (
                    <button type="button" onClick={() => setDialogo("diferencia")} className="rounded-sm bg-finance px-3 py-1 text-xs text-white hover:opacity-90">
                      Aceptar diferencia con motivo…
                    </button>
                  )}
                </div>
                {dialogo === "diferencia" && (
                  <MotivoForm
                    opciones={MOTIVOS_DIFERENCIA}
                    titulo={`Aceptar una diferencia de ${formatMoneda(preview.diferencia)} — ¿por qué?`}
                    confirmar="Aceptar y vincular"
                    ocupado={guardando}
                    onCancel={() => setDialogo(null)}
                    onConfirm={(motivo, detalle) =>
                      ejecutar(() => vincularComprasLote(idLineaConsumo, idsOrdenados, { motivo, detalle }), "Conciliada con diferencia aceptada.")
                    }
                  />
                )}
              </>
            )}

            {modoReparto && seleccion.length > 0 && propuesta && (
              <>
                <p className="text-xs font-medium text-ink-secondary">Reparto propuesto (editable) — {lineasReparto.length} líneas contra {seleccion.length} documentos</p>
                <div className="mt-1 overflow-auto">
                  <table className="w-full text-xs">
                    <thead className="text-left text-ink-secondary">
                      <tr>
                        <th className="py-0.5 pr-2">Línea</th>
                        <th className="pr-2">Documento</th>
                        <th className="text-right">Importe imputado</th>
                      </tr>
                    </thead>
                    <tbody>
                      {repartoEdit.map((r, i) => {
                        const d = porId.get(r.idCompra) ?? propuesta.documentos.find((x) => x.idCompra === r.idCompra);
                        return (
                          <tr key={`${r.idLinea}-${r.idCompra}-${i}`} className="border-t border-border">
                            <td className="py-0.5 pr-2">#{r.idLinea}</td>
                            <td className="pr-2">{d ? nombreDoc(d) : `#${r.idCompra}`}</td>
                            <td className="text-right">
                              <MoneyInput
                                className={`${filterInputClass} w-36 px-1.5 py-0.5 text-right text-xs font-data`}
                                moneda="Pesos"
                                value={r.importe}
                                onChange={(importe) => setRepartoEdit((prev) => prev.map((x, j) => (j === i ? { ...x, importe } : x)))}
                              />
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                <ul className="mt-1 text-xs">
                  {diferenciasReparto.map((d) => (
                    <li key={d.idLinea} className={d.cierra ? "text-status-success" : "text-status-danger"}>
                      Línea #{d.idLinea} ({formatMoneda(d.importe)}): {d.cierra ? "cierra" : `diferencia ${formatMoneda(d.diferencia)}`}
                    </li>
                  ))}
                </ul>
                <div className="mt-2 flex flex-wrap gap-2">
                  {!repartoNoCierra && (
                    <button
                      type="button"
                      disabled={guardando}
                      onClick={() => ejecutar(() => conciliarReparto(repartoEdit), "Reparto guardado.")}
                      className="rounded-sm bg-finance px-3 py-1 text-xs text-white hover:opacity-90 disabled:opacity-40"
                    >
                      Guardar reparto
                    </button>
                  )}
                  {repartoNoCierra && (
                    <button type="button" onClick={() => setDialogo("diferencia")} className="rounded-sm bg-finance px-3 py-1 text-xs text-white hover:opacity-90">
                      Aceptar diferencia con motivo…
                    </button>
                  )}
                </div>
                {dialogo === "diferencia" && (
                  <MotivoForm
                    opciones={MOTIVOS_DIFERENCIA}
                    titulo="Hay líneas que no cierran — ¿por qué se acepta la diferencia?"
                    confirmar="Aceptar y guardar"
                    ocupado={guardando}
                    onCancel={() => setDialogo(null)}
                    onConfirm={(motivo, detalle) => ejecutar(() => conciliarReparto(repartoEdit, { motivo, detalle }), "Reparto guardado con diferencia aceptada.")}
                  />
                )}
              </>
            )}

            {seleccion.length === 0 && (
              <p className="text-xs text-ink-secondary">Elegí uno o más documentos para ver si cierran con la línea.</p>
            )}

            {error && <p className="mt-2 text-xs text-status-danger">{error}</p>}

            <div className="mt-3 flex flex-wrap items-center gap-3 border-t border-border pt-2 text-xs">
              <button type="button" onClick={() => setDialogo("sinDocumento")} className="text-finance underline">
                Sin documento / no aplica…
              </button>
              <Link href={`/compras/nueva?${compraParams.toString()}`} target="_blank" className="text-finance underline">
                Cargar la compra
              </Link>
            </div>
            {dialogo === "sinDocumento" && (
              <MotivoForm
                opciones={MOTIVOS_SIN_DOCUMENTO}
                titulo="Marcar esta línea sin documento — ¿por qué?"
                confirmar="Marcar sin documento"
                ocupado={guardando}
                onCancel={() => setDialogo(null)}
                onConfirm={(motivo, detalle) => ejecutar(() => marcarSinDocumento(idLineaConsumo, motivo, detalle), "Línea marcada sin documento.")}
              />
            )}
          </div>
        )}
      </section>
    </div>
  );
}
