"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import {
  fetchVentasHacienda,
  type DocumentoRelacionadoVentaHacienda,
} from "@/services/ventasHaciendaApi";
import { filterInputClass } from "@/components/ui/FilterBar";

/**
 * Vínculo manual entre ventas de hacienda del mismo consignatario (ej. una
 * Nota de Crédito/Débito que complementa el documento original) — mismo
 * patrón que `DocumentosRelacionadosPanel` de Compras (006), adaptado acá
 * porque el contrato de búsqueda es distinto (`fetchVentasHacienda` no
 * admite filtrar por tipo de documento ni excluir por id todavía, así que
 * el filtrado de candidatos ya vinculados/self se hace en el cliente).
 */
export function DocumentosRelacionadosVentaHaciendaPanel({
  idConsignatario,
  relacionados,
  onVincular,
  onDesvincular,
  excluirIdVenta,
}: {
  idConsignatario: number | null;
  relacionados: DocumentoRelacionadoVentaHacienda[];
  onVincular: (doc: DocumentoRelacionadoVentaHacienda) => void;
  onDesvincular: (idVenta: number) => void;
  excluirIdVenta?: number;
}) {
  const [busqueda, setBusqueda] = useState("");
  const buscando = busqueda.trim().length >= 2;

  const { data: resultados, isFetching } = useQuery({
    queryKey: ["ventas-hacienda-relacionar", idConsignatario, busqueda],
    queryFn: () => fetchVentasHacienda({ consignatario: undefined, pageSize: 50 }),
    enabled: idConsignatario != null && buscando,
  });

  const idsRelacionados = new Set(relacionados.map((r) => r.idVenta));
  const candidatos = (resultados?.items ?? [])
    .filter((v) => v.idConsignatario === idConsignatario)
    .filter((v) => (v.numeroDocumento ?? "").toLowerCase().includes(busqueda.trim().toLowerCase()))
    .filter((v) => v.idVenta !== excluirIdVenta && !idsRelacionados.has(v.idVenta))
    .map((v) => ({
      idVenta: v.idVenta,
      fecha: v.fecha,
      tipoDocumento: null,
      numeroDocumento: v.numeroDocumento,
    }));

  return (
    <div className="rounded-md border border-border bg-surface p-2">
      <h3 className="text-xs font-medium text-ink-secondary">Documentos relacionados</h3>

      {relacionados.length > 0 && (
        <div className="mt-1 flex max-h-16 w-full flex-wrap gap-x-3 gap-y-1 overflow-y-auto">
          {relacionados.map((r) => (
            <label key={r.idVenta} className="flex cursor-pointer items-center gap-1 text-xs whitespace-nowrap">
              <input type="checkbox" checked onChange={() => onDesvincular(r.idVenta)} />
              <Link
                href={`/ventas/hacienda/${r.idVenta}/editar`}
                onClick={(e) => e.stopPropagation()}
                className="text-ink-secondary underline decoration-dotted hover:text-finance"
              >
                {r.fecha ?? "—"} · {r.tipoDocumento ?? "—"} {r.numeroDocumento ?? ""}
              </Link>
            </label>
          ))}
        </div>
      )}

      {idConsignatario == null && (
        <p className="mt-1 text-xs text-ink-muted">Elegí un consignatario para ver sus documentos.</p>
      )}
      {idConsignatario != null && (
        <input
          className={`${filterInputClass} mt-1 w-full px-1.5 py-0.5 text-xs`}
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          placeholder="Buscar nº de documento de este consignatario para relacionar…"
        />
      )}

      {buscando && isFetching && <p className="mt-1 text-xs text-ink-muted">Buscando…</p>}
      {buscando && !isFetching && candidatos.length > 0 && (
        <div className="mt-1 flex max-h-20 w-full flex-wrap gap-x-3 gap-y-1 overflow-y-auto">
          {candidatos.map((c) => (
            <label key={c.idVenta} className="flex cursor-pointer items-center gap-1 text-xs whitespace-nowrap">
              <input type="checkbox" checked={false} onChange={() => onVincular(c)} />
              <Link
                href={`/ventas/hacienda/${c.idVenta}/editar`}
                onClick={(e) => e.stopPropagation()}
                className="text-ink-secondary underline decoration-dotted hover:text-finance"
              >
                {c.fecha ?? "—"} · {c.numeroDocumento ?? ""}
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
