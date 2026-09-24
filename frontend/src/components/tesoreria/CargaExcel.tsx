"use client";

import { useState } from "react";

import {
  confirmarCargaExcel,
  previsualizarConfirmacion,
  type ExcelConfirmacionResponse,
  type ExcelPrevisualizacionConfirmacionResponse,
} from "@/services/tesoreriaApi";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatCantidad } from "@/lib/format";

const ESTADO_LABEL: Record<string, string> = {
  nuevo: "Nuevo",
  omitidoDuplicado: "Ya existe",
  omitidoIncompleto: "Incompleto",
};

/**
 * Upload + preview + confirm for BNA/Galicia Excel summaries (003 US3 +
 * 013 US1-US4). La previsualización siempre corre primero y nunca persiste
 * (FR-004); solo "Confirmar carga" escribe en `WC`, reprocesando el mismo
 * archivo (FR-002) en vez de reusar la vista previa en memoria.
 */
export function CargaExcel() {
  const [archivo, setArchivo] = useState<File | null>(null);
  const [resultado, setResultado] = useState<ExcelPrevisualizacionConfirmacionResponse | null>(null);
  const [confirmacion, setConfirmacion] = useState<ExcelConfirmacionResponse | null>(null);
  const [cargando, setCargando] = useState(false);
  const [confirmando, setConfirmando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const seleccionado = e.target.files?.[0];
    if (!seleccionado) return;

    setArchivo(seleccionado);
    setCargando(true);
    setError(null);
    setResultado(null);
    setConfirmacion(null);
    try {
      const respuesta = await previsualizarConfirmacion(seleccionado);
      setResultado(respuesta);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setCargando(false);
    }
  }

  async function handleConfirmar() {
    if (!archivo) return;
    setConfirmando(true);
    setError(null);
    try {
      const respuesta = await confirmarCargaExcel(archivo);
      setConfirmacion(respuesta);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setConfirmando(false);
    }
  }

  return (
    <section className="rounded-md border border-border bg-surface p-4">
      <h3 className="text-sm font-semibold text-ink-primary">
        Cargar resumen bancario (BNA / Galicia, Excel)
      </h3>
      <p className="mt-1 text-xs italic text-ink-secondary">
        La vista previa nunca escribe nada. Solo &quot;Confirmar carga&quot; persiste los movimientos
        nuevos en el sistema.
      </p>

      <input
        type="file"
        accept=".xls,.xlsx"
        className="mt-3 text-sm"
        onChange={handleFileChange}
      />

      {cargando && (
        <div className="mt-3">
          <LoadingState rows={2} />
        </div>
      )}

      {error && (
        <div className="mt-3">
          <ErrorState message={`Error: ${error}`} />
        </div>
      )}

      {resultado && !resultado.valido && (
        <div className="mt-3 rounded-sm border border-status-danger bg-status-danger-bg p-3 text-sm text-status-danger">
          <p className="font-semibold">Archivo inválido</p>
          <ul className="list-disc pl-4">
            {resultado.errores.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </div>
      )}

      {resultado && resultado.valido && resultado.resumen && (
        <div className="mt-3 space-y-3">
          <p className="text-sm text-status-success">
            Medio detectado: <strong>{resultado.medioDetectado}</strong> —{" "}
            {formatCantidad(resultado.resumen.nuevos)} nuevos,{" "}
            {formatCantidad(resultado.resumen.omitidosDuplicado)} ya existentes
            {resultado.resumen.omitidosIncompletos > 0
              ? `, ${formatCantidad(resultado.resumen.omitidosIncompletos)} incompletos`
              : ""}{" "}
            (de {formatCantidad(resultado.resumen.total)} filas).
          </p>

          {!confirmacion && (
            <button
              type="button"
              onClick={handleConfirmar}
              disabled={confirmando || resultado.resumen.nuevos === 0}
              className="rounded-md bg-finance px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
            >
              {confirmando ? "Confirmando..." : "Confirmar carga"}
            </button>
          )}

          {confirmacion && confirmacion.valido && (
            <p className="rounded-sm border border-status-success bg-status-success-bg p-2 text-sm text-status-success">
              Carga #{confirmacion.idCarga} confirmada: {formatCantidad(confirmacion.insertados ?? 0)}{" "}
              movimientos insertados, {formatCantidad(confirmacion.omitidosDuplicado ?? 0)} omitidos por
              ya existir.
            </p>
          )}

          <div className="max-h-96 overflow-auto rounded border border-border">
            <table className="min-w-full divide-y divide-border text-xs">
              <thead className="bg-surface-sunken text-left">
                <tr>
                  {resultado.movimientosPrevisualizados[0] &&
                    Object.keys(resultado.movimientosPrevisualizados[0]).map((key) => (
                      <th key={key} className="px-2 py-1">
                        {key === "estado" ? "Estado" : key}
                      </th>
                    ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {resultado.movimientosPrevisualizados.map((mov, i) => (
                  <tr key={i}>
                    {Object.entries(mov).map(([key, value]) => (
                      <td key={key} className="px-2 py-1">
                        {key === "estado"
                          ? ESTADO_LABEL[value as string] ?? String(value)
                          : Array.isArray(value)
                            ? value.join(", ")
                            : String(value ?? "—")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}
