"use client";

import { useState } from "react";

import { validarExcel, type ExcelValidacionResponse } from "@/services/tesoreriaApi";

/**
 * Upload + preview for bank/tarjeta Excel summaries (US3: FR-007/008/009).
 * Always shows an explicit "no persistido todavía" notice — this endpoint
 * only validates and previews, it never writes to SQL Server.
 */
export function CargaExcel() {
  const [resultado, setResultado] = useState<ExcelValidacionResponse | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const archivo = e.target.files?.[0];
    if (!archivo) return;

    setCargando(true);
    setError(null);
    setResultado(null);
    try {
      const respuesta = await validarExcel(archivo);
      setResultado(respuesta);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setCargando(false);
    }
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-slate-700">
        Cargar resumen bancario o de tarjeta (Excel)
      </h3>
      <p className="mt-1 text-xs italic text-slate-500">
        Esta carga solo valida y previsualiza el archivo. No persiste nada todavía.
      </p>

      <input
        type="file"
        accept=".xls,.xlsx"
        className="mt-3 text-sm"
        onChange={handleFileChange}
      />

      {cargando && <p className="mt-3 text-slate-600">Validando…</p>}

      {error && <p className="mt-3 text-red-700">Error al validar el archivo: {error}</p>}

      {resultado && !resultado.valido && (
        <div className="mt-3 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          <p className="font-semibold">Archivo inválido</p>
          <ul className="list-disc pl-4">
            {resultado.errores.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </div>
      )}

      {resultado && resultado.valido && (
        <div className="mt-3 space-y-2">
          <p className="text-sm text-emerald-700">
            Medio detectado: <strong>{resultado.medioDetectado}</strong> —{" "}
            {resultado.movimientosPrevisualizados.length} movimientos previsualizados (no
            persistido todavía).
          </p>
          <div className="max-h-96 overflow-auto rounded border border-slate-200">
            <table className="min-w-full divide-y divide-slate-200 text-xs">
              <thead className="bg-slate-100 text-left">
                <tr>
                  {resultado.movimientosPrevisualizados[0] &&
                    Object.keys(resultado.movimientosPrevisualizados[0]).map((key) => (
                      <th key={key} className="px-2 py-1">
                        {key}
                      </th>
                    ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {resultado.movimientosPrevisualizados.map((mov, i) => (
                  <tr key={i}>
                    {Object.values(mov).map((value, j) => (
                      <td key={j} className="px-2 py-1">
                        {Array.isArray(value) ? value.join(", ") : String(value ?? "—")}
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
