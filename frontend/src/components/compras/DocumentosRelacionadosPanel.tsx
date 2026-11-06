"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { fetchCompras, type DocumentoRelacionado, type TipoDocumentoCompra } from "@/services/comprasApi";
import { formatFecha, formatMoneda } from "@/lib/format";

/** Un documento suele relacionarse con el/los tipo/s "opuesto/s" — una
 *  Nota de Crédito o Débito complementa una Factura, y viceversa. */
function tiposCandidatos(tipoActual: TipoDocumentoCompra): TipoDocumentoCompra[] {
  if (tipoActual === "Nota de Crédito" || tipoActual === "Nota de Débito") {
    return ["Factura"];
  }
  if (tipoActual === "Factura") {
    return ["Nota de Crédito", "Nota de Débito"];
  }
  return [];
}

/**
 * Vínculo manual entre documentos del mismo proveedor (ej. una Nota de Crédito/Débito que complementa una Factura).
 * 06/11/2026 (Sergio): lista tildable filtrada sola por proveedor y tipo complementario — tipear el nº es poco
 * práctico. Para que no se haga larga: se abre a pedido, ordenada por cercanía a la fecha del documento, 12 a la vista
 * y "Ver más" para el resto.
 */
export function DocumentosRelacionadosPanel({
  idContacto,
  tipoDocumento,
  relacionados,
  onVincular,
  onDesvincular,
  excluirIdCompra,
  fechaReferencia,
}: {
  idContacto: number | null;
  tipoDocumento: TipoDocumentoCompra;
  relacionados: DocumentoRelacionado[];
  onVincular: (doc: DocumentoRelacionado) => void;
  onDesvincular: (idCompra: number) => void;
  /** No ofrecer este id como candidato (la propia compra, si ya tiene id). */
  excluirIdCompra?: number;
  /** Fecha del documento que se edita: los candidatos más cercanos van primero. */
  fechaReferencia?: string | null;
}) {
  const [abierto, setAbierto] = useState(false);
  const [verTodos, setVerTodos] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const tipos = tiposCandidatos(tipoDocumento);

  useEffect(() => {
    if (!abierto) return;
    const cerrar = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setAbierto(false);
    };
    document.addEventListener("mousedown", cerrar);
    return () => document.removeEventListener("mousedown", cerrar);
  }, [abierto]);

  const { data: resultados, isFetching } = useQuery({
    queryKey: ["compras-relacionar", idContacto, tipos],
    queryFn: () => fetchCompras({ idContacto: idContacto!, tipoDocumento: tipos, pageSize: 200 }),
    enabled: abierto && idContacto != null && tipos.length > 0,
  });

  const idsRelacionados = new Set(relacionados.map((r) => r.idCompra));
  const ref0 = fechaReferencia ? new Date(fechaReferencia).getTime() : Date.now();
  const candidatos = (resultados?.items ?? [])
    .filter((c) => c.idCompra !== excluirIdCompra && !idsRelacionados.has(c.idCompra))
    .sort((a, b) => Math.abs(new Date(a.fecha ?? 0).getTime() - ref0) - Math.abs(new Date(b.fecha ?? 0).getTime() - ref0));
  const visibles = verTodos ? candidatos : candidatos.slice(0, 12);

  const etiqueta = (r: { fecha: string | null; tipoDocumento: string | null; numeroDocumento: string | null }) =>
    `${formatFecha(r.fecha)} · ${r.tipoDocumento ?? "—"} ${r.numeroDocumento ?? ""}`;

  return (
    <div ref={ref} className="relative flex h-7 items-center gap-2 rounded border border-border bg-surface px-2 text-xs">
      <span className="shrink-0 font-medium text-ink-secondary">Documentos relacionados:</span>
      <div className="flex min-w-0 flex-1 items-center gap-x-3 overflow-x-auto">
        {relacionados.length > 0 ? (
          relacionados.map((r) => (
            <label key={r.idCompra} className="flex cursor-pointer items-center gap-1 whitespace-nowrap">
              <input type="checkbox" checked onChange={() => onDesvincular(r.idCompra)} />
              <Link href={`/compras/${r.idCompra}/editar`} className="text-ink-secondary underline decoration-dotted hover:text-finance">
                {etiqueta(r)}
              </Link>
            </label>
          ))
        ) : (
          <span className="text-ink-muted">ninguno</span>
        )}
      </div>
      {idContacto == null && <span className="shrink-0 text-ink-muted">Elegí un proveedor</span>}
      {idContacto != null && tipos.length === 0 && <span className="shrink-0 text-ink-muted">No aplica a {tipoDocumento}</span>}
      {idContacto != null && tipos.length > 0 && (
        <button type="button" onClick={() => setAbierto(!abierto)} className="shrink-0 text-finance hover:underline">
          {abierto ? "Cerrar" : `Relacionar ${tipos.join("/")}`}
        </button>
      )}
      {abierto && (
        <div className="absolute right-0 top-full z-20 mt-1 w-[30rem] max-w-full rounded border border-border-strong bg-surface p-2 shadow-lg">
          {isFetching && <p className="text-ink-muted">Cargando…</p>}
          {!isFetching && candidatos.length === 0 && (
            <p className="text-ink-muted">Este proveedor no tiene otros documentos de tipo {tipos.join("/")}.</p>
          )}
          {!isFetching && candidatos.length > 0 && (
            <div className="flex max-h-56 flex-col overflow-y-auto">
              {visibles.map((c) => (
                <label key={c.idCompra} className="flex cursor-pointer items-center gap-2 rounded px-1 py-0.5 hover:bg-surface-sunken">
                  <input
                    type="checkbox"
                    checked={false}
                    onChange={() => onVincular({ idCompra: c.idCompra, fecha: c.fecha, tipoDocumento: c.tipoDocumento, numeroDocumento: c.numeroDocumento })}
                  />
                  <span className="flex-1">{etiqueta(c)}</span>
                  {c.importeDocumento != null && <span className="tabular-nums text-ink-secondary">{formatMoneda(c.importeDocumento)}</span>}
                </label>
              ))}
              {!verTodos && candidatos.length > visibles.length && (
                <button type="button" onClick={() => setVerTodos(true)} className="mt-1 text-left text-finance hover:underline">
                  Ver más ({candidatos.length - visibles.length})
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
