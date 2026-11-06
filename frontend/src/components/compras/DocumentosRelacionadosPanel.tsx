"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { fetchCompras, type DocumentoRelacionado, type TipoDocumentoCompra } from "@/services/comprasApi";
import { filterInputClass } from "@/components/ui/FilterBar";
import { formatFecha } from "@/lib/format";

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

  const lista = (docs: DocumentoRelacionado[], vinculados: boolean) =>
    docs.map((r) => (
      <label key={r.idCompra} className="flex cursor-pointer items-center gap-1 whitespace-nowrap text-xs">
        <input
          type="checkbox"
          checked={vinculados}
          onChange={() => (vinculados ? onDesvincular(r.idCompra) : onVincular(r))}
        />
        <Link
          href={`/compras/${r.idCompra}/editar`}
          onClick={(e) => e.stopPropagation()}
          className="text-ink-secondary underline decoration-dotted hover:text-finance"
        >
          {formatFecha(r.fecha)} · {r.tipoDocumento ?? "—"} {r.numeroDocumento ?? ""}
        </Link>
      </label>
    ));

  // Franja de una línea: lo vinculado (tildado) + buscador; los resultados se abren debajo sin empujar la grilla.
  return (
    <div className="relative flex h-7 items-center gap-2 rounded border border-border bg-surface px-2 text-xs">
      <span className="shrink-0 font-medium text-ink-secondary">Documentos relacionados:</span>
      <div className="flex min-w-0 flex-1 items-center gap-x-3 overflow-x-auto">
        {relacionados.length > 0 ? lista(relacionados, true) : <span className="text-ink-muted">ninguno</span>}
      </div>
      {idContacto == null && <span className="shrink-0 text-ink-muted">Elegí un proveedor</span>}
      {idContacto != null && tipos.length === 0 && (
        <span className="shrink-0 text-ink-muted">No aplica a {tipoDocumento}</span>
      )}
      {idContacto != null && tipos.length > 0 && (
        <input
          className={`${filterInputClass} h-5 w-52 shrink-0 px-1.5 py-0 text-xs`}
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          onKeyDown={(e) => e.key === "Escape" && setBusqueda("")}
          placeholder={`Buscar nº de ${tipos.join("/")}…`}
          aria-label={`Buscar nº de ${tipos.join("/")} de este proveedor para relacionar`}
        />
      )}
      {buscando && (
        <div className="absolute right-0 top-full z-20 mt-1 w-[28rem] max-w-full rounded border border-border-strong bg-surface p-2 shadow-lg">
          {isFetching && <p className="text-ink-muted">Buscando…</p>}
          {!isFetching && candidatos.length > 0 && (
            <div className="flex max-h-40 flex-col gap-1 overflow-y-auto">{lista(candidatos, false)}</div>
          )}
          {!isFetching && resultados && candidatos.length === 0 && (
            <p className="text-ink-muted">Sin resultados para &quot;{busqueda}&quot;.</p>
          )}
        </div>
      )}
    </div>
  );
}
