"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import {
  fetchCandidatosLinea,
  fetchConciliacionPreview,
  vincularComprasLote,
  type ConciliacionCalculo,
  type DocumentoCandidato,
} from "@/services/tarjetasResumenesApi";
import { formatMoneda, formatMonto } from "@/lib/format";
import { useToast } from "@/components/ui/Toast";

const nombreDoc = (d: DocumentoCandidato) => `${d.tipoDocumento ?? "Documento"} ${d.numeroDocumento ?? ""}`.trim();

const importeOriginal = (d: DocumentoCandidato) =>
  formatMoneda(d.importeOriginal, d.moneda === "Dolares" ? "Dolares" : "Pesos");

const porcentaje = (v: number) => `${v > 0 ? "+" : ""}${(v * 100).toLocaleString("es-AR", { maximumFractionDigits: 2 })}%`;

/** Resultado de una conciliación (sugerida o de la selección manual). */
function ResumenCalculo({ calculo, importeLinea }: { calculo: ConciliacionCalculo; importeLinea: number }) {
  const conTc = calculo.tcImplicito != null;
  const cierra = calculo.estado !== "parcial";
  return (
    <div className="text-xs">
      <span className={cierra ? "font-medium text-status-success" : "font-medium text-status-danger"}>
        {calculo.estado === "exacta" && "Coincide"}
        {calculo.estado === "aproximada" &&
          (Math.abs(calculo.desvioTc ?? 1) <= 0.005
            ? "Coincide"
            : "Posible coincidencia (el tipo de cambio de la tarjeta difiere): verificalo")}
        {calculo.estado === "parcial" && (calculo.pagoParcial ? "Pago parcial del documento" : "No cierra")}
      </span>
      {conTc && (
        <span className="text-ink-secondary">
          {" "}
          · TC implícito {formatMonto(calculo.tcImplicito!)}
          {calculo.tcReferencia != null && (
            <>
              {" "}
              vs {formatMonto(calculo.tcReferencia)} del documento
              {calculo.desvioTc != null && ` (${porcentaje(calculo.desvioTc)})`}
            </>
          )}
        </span>
      )}
      {!conTc && calculo.estado === "parcial" && !calculo.pagoParcial && (
        <span className="text-ink-secondary">
          {" "}
          · diferencia {formatMoneda(calculo.diferencia)} sobre {formatMoneda(importeLinea)}
        </span>
      )}
    </div>
  );
}

/**
 * Documentos candidatos para conciliar una línea de consumo del resumen. Los
 * documentos en dólares se muestran pesificados (el resumen siempre viene en
 * pesos), se pueden elegir varios (Factura + Nota de Crédito/Débito) para
 * saldar la cuenta, y se sugieren las combinaciones que cierran con la línea.
 */
export function CandidatosDocumentos({
  idLineaConsumo,
  onLinked,
}: {
  idLineaConsumo: number;
  onLinked: () => void;
}) {
  const { showToast } = useToast();
  const [seleccion, setSeleccion] = useState<number[]>([]);
  const [guardando, setGuardando] = useState(false);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["linea-candidatos", idLineaConsumo],
    queryFn: () => fetchCandidatosLinea(idLineaConsumo),
    staleTime: 0,
    gcTime: 0,
  });

  const seleccionOrdenada = [...seleccion].sort((a, b) => a - b);
  const { data: preview } = useQuery({
    queryKey: ["linea-conciliacion", idLineaConsumo, seleccionOrdenada],
    queryFn: () => fetchConciliacionPreview(idLineaConsumo, seleccionOrdenada),
    enabled: seleccion.length > 0,
    staleTime: 0,
  });

  async function vincular(ids: number[]) {
    setGuardando(true);
    try {
      await vincularComprasLote(idLineaConsumo, ids);
      showToast(ids.length === 1 ? "Documento vinculado." : `${ids.length} documentos vinculados.`, "success");
      onLinked();
    } catch {
      showToast("No se pudieron vincular los documentos.", "danger");
    } finally {
      setGuardando(false);
    }
  }

  function alternar(id: number) {
    setSeleccion((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  if (isLoading) return <p className="mt-1 text-xs text-ink-secondary">Buscando documentos del proveedor…</p>;
  if (isError || !data)
    return <p className="mt-1 text-xs text-status-danger">No se pudieron cargar los documentos candidatos.</p>;

  const porId = new Map(data.documentos.map((d) => [d.idCompra, d]));

  if (data.idContacto == null || data.documentos.length === 0) {
    return (
      <p className="mt-1 text-xs text-ink-secondary">
        {data.idContacto == null
          ? "Esta línea no tiene proveedor asociado: buscá el documento por proveedor o número."
          : "El proveedor de esta línea no tiene documentos cargados: buscá por otro proveedor o número."}
      </p>
    );
  }

  return (
    <div className="mt-1 space-y-2 rounded-sm border border-dashed border-border p-2">
      {data.sugerencias.length > 0 && (
        <div>
          <p className="text-xs font-medium text-ink-secondary">
            Combinaciones que concilian {formatMoneda(data.importeLinea)}
          </p>
          <ul className="mt-1 space-y-1">
            {data.sugerencias.map((s) => (
              <li
                key={s.idsCompra.join("-")}
                className="flex flex-wrap items-center justify-between gap-2 rounded-sm bg-surface-sunken px-2 py-1"
              >
                <div className="min-w-0">
                  <div className="text-xs">
                    {s.idsCompra.map((id, i) => {
                      const d = porId.get(id);
                      return (
                        <span key={id}>
                          {i > 0 && <span className="text-ink-secondary"> + </span>}
                          {d ? `${nombreDoc(d)} (${importeOriginal(d)})` : `#${id}`}
                        </span>
                      );
                    })}
                  </div>
                  <ResumenCalculo calculo={s} importeLinea={data.importeLinea} />
                </div>
                <button
                  type="button"
                  disabled={guardando}
                  onClick={() => vincular(s.idsCompra)}
                  className="rounded-sm bg-finance px-2 py-0.5 text-xs text-white hover:opacity-90 disabled:opacity-40"
                >
                  Vincular
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div>
        <p className="text-xs font-medium text-ink-secondary">
          Documentos del proveedor — tildá uno o más para conciliar {formatMoneda(data.importeLinea)}
        </p>
        <div className="mt-1 max-h-64 overflow-auto">
          <table className="w-full text-xs">
            <thead className="text-left text-ink-secondary">
              <tr>
                <th className="w-6" />
                <th className="py-0.5 pr-2">Fecha</th>
                <th className="pr-2">Documento</th>
                <th className="pr-2 text-right">Importe original</th>
                <th className="pr-2 text-right">TC</th>
                <th className="text-right">Importe en $</th>
              </tr>
            </thead>
            <tbody>
              {data.documentos.map((d) => (
                <tr
                  key={d.idCompra}
                  className={`cursor-pointer border-t border-border hover:bg-surface-sunken ${
                    seleccion.includes(d.idCompra) ? "bg-finance-light" : ""
                  }`}
                  onClick={() => alternar(d.idCompra)}
                >
                  <td className="py-0.5">
                    <input
                      type="checkbox"
                      checked={seleccion.includes(d.idCompra)}
                      onChange={() => alternar(d.idCompra)}
                      onClick={(e) => e.stopPropagation()}
                      aria-label={`Elegir ${nombreDoc(d)}`}
                    />
                  </td>
                  <td className="py-0.5 pr-2 whitespace-nowrap">{d.fecha ?? "—"}</td>
                  <td className="pr-2">
                    {nombreDoc(d)}
                    {d.vinculosPrevios > 0 && (
                      <span
                        className="ml-1 text-ink-secondary"
                        title="Este documento ya está vinculado a otras líneas (ej. cuotas)"
                      >
                        · en {d.vinculosPrevios} línea{d.vinculosPrevios > 1 ? "s" : ""}
                      </span>
                    )}
                  </td>
                  <td className="pr-2 text-right font-data whitespace-nowrap">{importeOriginal(d)}</td>
                  <td className="pr-2 text-right font-data">
                    {d.moneda === "Dolares" && d.tipoDeCambio ? formatMonto(d.tipoDeCambio) : "—"}
                  </td>
                  <td className="text-right font-data whitespace-nowrap">{formatMoneda(d.importePesos)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {seleccion.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-sm bg-surface-sunken px-2 py-1">
          <div>
            <div className="text-xs">
              {seleccion.length} documento{seleccion.length > 1 ? "s" : ""} · línea {formatMoneda(data.importeLinea)}
              {preview && ` · total imputado ${formatMoneda(preview.imputados.reduce((a, i) => a + i.importeImputado, 0))}`}
            </div>
            {preview && <ResumenCalculo calculo={preview} importeLinea={data.importeLinea} />}
          </div>
          <div className="flex gap-1">
            <button
              type="button"
              onClick={() => setSeleccion([])}
              className="rounded-sm border border-border px-2 py-0.5 text-xs text-ink-secondary hover:text-ink-primary"
            >
              Limpiar
            </button>
            <button
              type="button"
              disabled={guardando || !preview}
              onClick={() => vincular(seleccionOrdenada)}
              className="rounded-sm bg-finance px-2 py-0.5 text-xs text-white hover:opacity-90 disabled:opacity-40"
            >
              {guardando ? "Vinculando…" : `Vincular ${seleccion.length}`}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
