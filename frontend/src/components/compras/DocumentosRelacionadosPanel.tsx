"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { fetchCompras, type DocumentoRelacionado, type TipoDocumentoCompra } from "@/services/comprasApi";
import { filterInputClass } from "@/components/ui/FilterBar";

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
 * Vínculo manual entre documentos del mismo proveedor (ej. una Nota de
 * Crédito/Débito que complementa una Factura, por devolución o ajuste de
 * tipo de cambio). Proveedores con muchos documentos del tipo
 * complementario hacían que listar automáticamente hasta 20 candidatos
 * fuera "engorroso y poco práctico" (pedido explícito del usuario,
 * 2026-09-17) — ahora es una búsqueda explícita por nº de documento (no
 * se pide nada hasta escribir, mismo patrón que `ContactoSelect`), así el
 * usuario encuentra el puntual que quiere relacionar en vez de tildar
 * entre una lista larga. Lo ya vinculado se sigue mostrando siempre,
 * tildable/destildable, sin necesidad de buscar.
 */
export function DocumentosRelacionadosPanel({
  idContacto,
  tipoDocumento,
  relacionados,
  onVincular,
  onDesvincular,
  excluirIdCompra,
}: {
  idContacto: number | null;
  tipoDocumento: TipoDocumentoCompra;
  relacionados: DocumentoRelacionado[];
  onVincular: (doc: DocumentoRelacionado) => void;
  onDesvincular: (idCompra: number) => void;
  /** No ofrecer este id como candidato (la propia compra, si ya tiene id). */
  excluirIdCompra?: number;
}) {
  const [busqueda, setBusqueda] = useState("");
  const tipos = tiposCandidatos(tipoDocumento);
  const buscando = busqueda.trim().length >= 2;

  const { data: resultados, isFetching } = useQuery({
    queryKey: ["compras-relacionar", idContacto, tipos, busqueda],
    queryFn: () =>
      fetchCompras({ idContacto: idContacto!, tipoDocumento: tipos, numeroDocumento: busqueda, pageSize: 10 }),
    enabled: idContacto != null && tipos.length > 0 && buscando,
  });

  const idsRelacionados = new Set(relacionados.map((r) => r.idCompra));
  const candidatos = (resultados?.items ?? []).filter(
    (c) => c.idCompra !== excluirIdCompra && !idsRelacionados.has(c.idCompra)
  );

  return (
    <div className="rounded-md border border-border bg-surface p-2">
      <h3 className="text-xs font-medium text-ink-secondary">Documentos relacionados</h3>

      {relacionados.length > 0 && (
        <div className="mt-1 flex max-h-16 w-full flex-wrap gap-x-3 gap-y-1 overflow-y-auto">
          {relacionados.map((r) => (
            <label key={r.idCompra} className="flex cursor-pointer items-center gap-1 text-xs whitespace-nowrap">
              <input type="checkbox" checked onChange={() => onDesvincular(r.idCompra)} />
              <Link
                href={`/compras/${r.idCompra}/editar`}
                onClick={(e) => e.stopPropagation()}
                className="text-ink-secondary underline decoration-dotted hover:text-finance"
              >
                {r.fecha ?? "—"} · {r.tipoDocumento ?? "—"} {r.numeroDocumento ?? ""}
              </Link>
            </label>
          ))}
        </div>
      )}

      {idContacto == null && (
        <p className="mt-1 text-xs text-ink-muted">Elegí un proveedor para ver sus documentos.</p>
      )}
      {idContacto != null && tipos.length === 0 && (
        <p className="mt-1 text-xs text-ink-muted">
          No aplica para tipo de documento &quot;{tipoDocumento}&quot;.
        </p>
      )}
      {idContacto != null && tipos.length > 0 && (
        <input
          className={`${filterInputClass} mt-1 w-full px-1.5 py-0.5 text-xs`}
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          placeholder={`Buscar nº de ${tipos.join("/")} de este proveedor para relacionar…`}
        />
      )}

      {buscando && isFetching && <p className="mt-1 text-xs text-ink-muted">Buscando…</p>}
      {buscando && !isFetching && candidatos.length > 0 && (
        <div className="mt-1 flex max-h-20 w-full flex-wrap gap-x-3 gap-y-1 overflow-y-auto">
          {candidatos.map((c) => (
            <label key={c.idCompra} className="flex cursor-pointer items-center gap-1 text-xs whitespace-nowrap">
              <input type="checkbox" checked={false} onChange={() => onVincular(c)} />
              <Link
                href={`/compras/${c.idCompra}/editar`}
                onClick={(e) => e.stopPropagation()}
                className="text-ink-secondary underline decoration-dotted hover:text-finance"
              >
                {c.fecha ?? "—"} · {c.tipoDocumento ?? "—"} {c.numeroDocumento ?? ""}
              </Link>
            </label>
          ))}
        </div>
      )}
      {buscando && !isFetching && resultados && candidatos.length === 0 && (
        <p className="mt-1 text-xs text-ink-muted">Sin resultados para &quot;{busqueda}&quot;.</p>
      )}
    </div>
  );
}
