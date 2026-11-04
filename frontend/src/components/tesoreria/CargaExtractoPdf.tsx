"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { confirmarExtractoPdf, previsualizarExtractoPdf, type ExtractoPdfResultado } from "@/services/tesoreriaApi";
import { LoadingState } from "@/components/ui/States";
import { formatCantidad, formatFecha, formatMoneda } from "@/lib/format";

/** Resumen bancario en PDF (Galicia o Banco Nación), 04/11/2026. La vista previa no escribe nada: muestra los
 * movimientos nuevos con el contacto que se les asigna; "Confirmar carga" los graba y guarda el PDF con los demás. */
export function CargaExtractoPdf() {
  const qc = useQueryClient();
  const [archivo, setArchivo] = useState<File | null>(null);
  const [vista, setVista] = useState<ExtractoPdfResultado | null>(null);
  const [hecho, setHecho] = useState<ExtractoPdfResultado | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function elegir(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    setArchivo(f);
    setVista(null);
    setHecho(null);
    setError(null);
    setCargando(true);
    try {
      setVista(await previsualizarExtractoPdf(f));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setCargando(false);
    }
  }

  async function confirmar() {
    if (!archivo) return;
    setCargando(true);
    setError(null);
    try {
      setHecho(await confirmarExtractoPdf(archivo));
      qc.invalidateQueries();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setCargando(false);
    }
  }

  const sinContacto = vista?.nuevos.filter((m) => m.sinContacto).length ?? 0;

  return (
    <section className="rounded-md border border-border bg-surface p-4">
      <h3 className="text-sm font-semibold text-ink-primary">Cargar resumen bancario en PDF (Galicia / Banco Nación)</h3>
      <p className="mt-1 text-xs text-ink-secondary">
        Elegí el PDF del resumen: primero se muestra lo que se va a cargar, sin grabar nada. Lo que ya estaba cargado
        no se repite.
      </p>
      <input type="file" accept=".pdf,application/pdf" className="mt-3 text-sm" onChange={elegir} />

      {cargando && <div className="mt-3"><LoadingState rows={2} /></div>}
      {error && (
        <p className="mt-3 rounded-sm border border-status-danger bg-status-danger-bg p-2 text-sm text-status-danger">{error}</p>
      )}

      {vista && !cargando && (
        <div className="mt-3 space-y-3">
          <p className="text-sm">
            <strong>{vista.banco}</strong>: {formatCantidad(vista.nuevos.length)} movimientos nuevos
            {vista.yaCargados > 0 && `, ${formatCantidad(vista.yaCargados)} ya estaban cargados`}
            {sinContacto > 0 && <span className="text-amber-900"> · {formatCantidad(sinContacto)} sin contacto (asignalo después en el movimiento)</span>}
          </p>

          {hecho ? (
            <p className="rounded-sm border border-status-success bg-status-success-bg p-2 text-sm text-status-success">
              Listo: se cargaron {formatCantidad(hecho.grabados ?? 0)} movimientos de {hecho.banco}.
            </p>
          ) : (
            <button type="button" onClick={confirmar} disabled={vista.nuevos.length === 0}
              className="rounded-md bg-finance px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50">
              Confirmar carga
            </button>
          )}

          {vista.nuevos.length > 0 && (
            <div className="max-h-96 overflow-auto rounded border border-border">
              <table className="min-w-full divide-y divide-border text-xs">
                <thead className="sticky top-0 bg-surface-sunken text-left">
                  <tr>
                    <th className="px-2 py-1">Fecha</th>
                    <th className="px-2 py-1">Descripción</th>
                    <th className="px-2 py-1 text-right">Importe</th>
                    <th className="px-2 py-1">Contacto</th>
                    <th className="px-2 py-1">Detalle del banco</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {vista.nuevos.map((m, i) => (
                    <tr key={i} className={m.sinContacto ? "bg-amber-50" : ""}>
                      <td className="whitespace-nowrap px-2 py-1">{formatFecha(m.fecha)}</td>
                      <td className="px-2 py-1">{m.descripcion}</td>
                      <td className={`whitespace-nowrap px-2 py-1 text-right ${m.importe < 0 ? "text-status-danger" : ""}`}>
                        {formatMoneda(m.importe)}
                      </td>
                      <td className="px-2 py-1">{m.sinContacto ? "Sin contacto" : m.contacto ?? "—"}</td>
                      <td className="px-2 py-1 text-ink-secondary">{m.detalle ?? ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
