"use client";

import Link from "next/link";

import { formatFecha, formatMoneda } from "@/lib/format";
import { urlDocumentoLocal } from "@/services/comprasApi";
import { ETIQUETA_CARGA, urlCargarEnCompras, type Documento } from "@/services/bovedaApi";

const COLOR_CARGA: Record<string, string> = {
  cargado_auto: "bg-agro-light text-agro",
  ya_cargado: "bg-surface-sunken text-ink-secondary",
  pendiente: "bg-amber-100 text-amber-800",
  historico: "bg-surface-sunken text-ink-muted",
  no_aplica: "bg-surface-sunken text-ink-secondary",
};

function carpeta(ruta: string | null): string {
  if (!ruta) return "—";
  const partes = ruta.split("\\");
  return partes.length > 1 ? partes[partes.length - 2] : "—";
}

/** Documentos bajados de los portales con su estado de carga en Compras (037 US2; 042 US3). */
export function DocumentosTabla({ documentos, vacio, conPortal = false }: { documentos: Documento[]; vacio: string; conPortal?: boolean }) {
  if (documentos.length === 0) {
    return <p className="py-4 text-sm text-ink-muted">{vacio}</p>;
  }
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-ink-muted">
          <th className="py-2 pr-3">Fecha</th>
          {conPortal && <th className="py-2 pr-3">Portal</th>}
          <th className="py-2 pr-3">Proveedor</th>
          <th className="py-2 pr-3">Comprobante</th>
          <th className="py-2 pr-3 text-right">Total</th>
          <th className="py-2 pr-3">Archivo</th>
          <th className="py-2 pr-3">Estado</th>
          <th className="py-2" />
        </tr>
      </thead>
      <tbody>
        {documentos.map((d) => (
          <tr key={d.idDocumento} className="border-b border-border/60 align-top">
            <td className="py-2 pr-3 whitespace-nowrap">{formatFecha(d.fechaDocumento)}</td>
            {conPortal && <td className="py-2 pr-3">{d.portal}</td>}
            <td className="py-2 pr-3">{d.proveedor}</td>
            <td className="py-2 pr-3 whitespace-nowrap">{d.numeroDocumento ?? "—"}</td>
            <td className="py-2 pr-3 text-right whitespace-nowrap">
              {d.totalImpreso == null ? "—" : formatMoneda(d.totalImpreso, d.moneda === "USD" ? "Dolares" : "Pesos")}
            </td>
            <td className="py-2 pr-3">
              <div>{d.nombreArchivo ?? "—"}</div>
              <div className="text-xs text-ink-muted">{carpeta(d.ruta)}</div>
            </td>
            <td className="py-2 pr-3">
              <span className={`rounded-sm px-2 py-0.5 text-xs ${COLOR_CARGA[d.estadoCarga] ?? ""}`}>
                {ETIQUETA_CARGA[d.estadoCarga]}
              </span>
              {d.motivo && d.estadoCarga === "pendiente" && (
                <div className="mt-1 max-w-xs text-xs text-ink-secondary">{d.motivo}</div>
              )}
            </td>
            <td className="py-2 whitespace-nowrap text-right">
              <div className="flex justify-end gap-3">
                {d.ruta && (
                  <a
                    href={urlDocumentoLocal(d.ruta)}
                    target="_blank"
                    rel="noreferrer"
                    className="text-finance hover:underline"
                    title="Si el archivo se movió o se borró, el visor informa que no se encuentra"
                  >
                    Ver PDF
                  </a>
                )}
                {d.idCompra ? (
                  <Link href={`/compras/${d.idCompra}/editar`} className="text-finance hover:underline">
                    Ver compra
                  </Link>
                ) : (
                  d.estadoCarga === "pendiente" && (
                    <Link href={urlCargarEnCompras(d)} className="text-finance hover:underline">
                      Cargar en Compras
                    </Link>
                  )
                )}
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
