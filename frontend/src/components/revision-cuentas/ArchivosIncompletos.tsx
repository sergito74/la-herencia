"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { formatFecha, formatMoneda } from "@/lib/format";
import { urlDocumentoLocal } from "@/services/comprasApi";
import { revisionCuentasApi, type EstadoArchivo } from "@/services/revisionCuentasApi";

const NOMBRE_ESTADO: Record<EstadoArchivo, string> = {
  "comprobante-legible-extension-incorrecta": "Comprobante legible con extensión incorrecta (descarga cortada)",
  "no-legible": "No se puede leer",
  vacio: "Archivo vacío",
  "imagen-revisar": "Imagen: revisar a mano",
};

/** Períodos fiscales (abril a marzo) desde el más nuevo, para elegir la carpeta a revisar. */
function periodosFiscales(): string[] {
  const hoy = new Date();
  const inicio = hoy.getMonth() >= 3 ? hoy.getFullYear() : hoy.getFullYear() - 1;
  const lista: string[] = [];
  for (let a = inicio; a >= 2011; a--) lista.push(`04 ${a} - 03 ${a + 1}`);
  return lista;
}

/**
 * Archivos de las carpetas de compras que están incompletos o hay que mirar a mano, y si su comprobante ya está cargado. Es solo una
 * lectura: el sistema no modifica, renombra ni borra ningún archivo.
 */
export function ArchivosIncompletos() {
  const periodos = periodosFiscales();
  const [periodo, setPeriodo] = useState(periodos[0]);
  const [estado, setEstado] = useState<EstadoArchivo | "">("");
  const { data, isLoading, isFetching, error } = useQuery({
    queryKey: ["revision-archivos", periodo, estado],
    queryFn: () => revisionCuentasApi.archivosIncompletos({ periodo, estado: estado || undefined }),
  });

  return (
    <section className="space-y-3 text-sm">
      <div className="flex flex-wrap items-end gap-3">
        <label className="block text-xs">
          Período fiscal{" "}
          <select value={periodo} onChange={(e) => setPeriodo(e.target.value)} className="rounded border border-line px-1 py-0.5">
            {periodos.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </label>
        <label className="block text-xs">
          Estado{" "}
          <select value={estado} onChange={(e) => setEstado(e.target.value as EstadoArchivo | "")} className="rounded border border-line px-1 py-0.5">
            <option value="">Todos</option>
            {(Object.keys(NOMBRE_ESTADO) as EstadoArchivo[]).map((e) => <option key={e} value={e}>{NOMBRE_ESTADO[e]}</option>)}
          </select>
        </label>
        {isFetching && <span className="text-xs text-ink-secondary">Revisando la carpeta…</span>}
      </div>
      {isLoading && <p className="text-ink-secondary">Revisando los archivos… (un período lleva unos segundos)</p>}
      {error && <p role="alert" className="text-status-danger">No se pudo revisar la carpeta.</p>}
      {data && (
        <>
          <p className="text-xs text-ink-secondary">{data.total} archivos por revisar en {data.raiz}</p>
          {data.archivos.length === 0 ? (
            <p className="text-status-success">No hay archivos incompletos en este período.</p>
          ) : (
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-ink-secondary">
                  <th className="py-1">Archivo</th>
                  <th>Proveedor</th>
                  <th>Fecha</th>
                  <th>Estado</th>
                  <th>Número</th>
                  <th className="text-right">Importe</th>
                  <th>Cargado</th>
                </tr>
              </thead>
              <tbody>
                {data.archivos.map((a) => (
                  <tr key={a.ruta} className="border-t border-line">
                    <td className="py-1">
                      <a className="text-finance underline" href={urlDocumentoLocal(a.ruta)} target="_blank" rel="noreferrer">{a.ruta.split("\\").pop()}</a>
                    </td>
                    <td>{a.proveedor}</td>
                    <td>{a.fecha ? formatFecha(a.fecha) : "—"}</td>
                    <td>{NOMBRE_ESTADO[a.estado]}</td>
                    <td>{a.numero ?? "—"}</td>
                    <td className="text-right">{a.importe === null ? "—" : formatMoneda(a.importe)}</td>
                    <td className={a.cargado ? "text-status-success" : "text-status-danger"}>{a.cargado ? "Ya está cargado" : "Falta cargar"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </section>
  );
}
