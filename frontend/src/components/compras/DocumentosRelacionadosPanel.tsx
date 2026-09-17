"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { fetchCompras, type DocumentoRelacionado } from "@/services/comprasApi";
import { filterInputClass } from "@/components/ui/FilterBar";

/**
 * Vínculo manual entre documentos (ej. una Nota de Crédito/Débito que
 * complementa una Factura, por devolución o ajuste de tipo de cambio),
 * para referencia futura. Componente controlado: busca y muestra una
 * LISTA de candidatos → el usuario SELECCIONA cuáles vincular. El padre
 * decide qué pasa con esa selección (guardar en el momento si la compra ya
 * existe, o dejarla pendiente hasta guardar si es un alta nueva).
 */
export function DocumentosRelacionadosPanel({
  relacionados,
  onVincular,
  onDesvincular,
  excluirIdCompra,
}: {
  relacionados: DocumentoRelacionado[];
  onVincular: (doc: DocumentoRelacionado) => void;
  onDesvincular: (idCompra: number) => void;
  /** No ofrecer este id como candidato (la propia compra, si ya tiene id). */
  excluirIdCompra?: number;
}) {
  const [busqueda, setBusqueda] = useState("");
  const [busquedaAplicada, setBusquedaAplicada] = useState("");

  const { data: resultados } = useQuery({
    queryKey: ["compras-buscar-relacionar", busquedaAplicada],
    queryFn: () => fetchCompras({ numeroDocumento: busquedaAplicada, pageSize: 10 }),
    enabled: busquedaAplicada.length >= 2,
  });

  const idsRelacionados = new Set(relacionados.map((r) => r.idCompra));

  return (
    <div className="rounded-md border border-border bg-surface p-2">
      <h3 className="text-xs font-medium text-ink-secondary">
        Documentos relacionados (ej. Notas de Crédito/Débito que complementan esta factura)
      </h3>

      {relacionados.length > 0 && (
        <ul className="mt-1 space-y-0.5 text-xs">
          {relacionados.map((r) => (
            <li key={r.idCompra} className="flex items-center justify-between gap-2">
              <Link href={`/compras/${r.idCompra}/editar`} className="text-finance underline">
                {r.fecha ?? "—"} · {r.tipoDocumento ?? "—"} {r.numeroDocumento ?? ""}
              </Link>
              <button
                type="button"
                onClick={() => onDesvincular(r.idCompra)}
                className="text-status-danger hover:underline"
              >
                Quitar
              </button>
            </li>
          ))}
        </ul>
      )}

      <form
        className="mt-1 flex items-center gap-1"
        onSubmit={(e) => {
          e.preventDefault();
          setBusquedaAplicada(busqueda);
        }}
      >
        <input
          className={`${filterInputClass} px-1.5 py-0.5 text-xs`}
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          placeholder="Buscar por nº de documento para relacionar…"
        />
        <button type="submit" className="rounded-sm border border-border px-2 py-0.5 text-xs text-ink-secondary">
          Buscar
        </button>
      </form>

      {resultados && resultados.items.length > 0 && (
        <ul className="mt-1 space-y-0.5 text-xs">
          {resultados.items
            .filter((c) => c.idCompra !== excluirIdCompra && !idsRelacionados.has(c.idCompra))
            .map((c) => (
              <li key={c.idCompra} className="flex items-center justify-between gap-2">
                <span className="text-ink-secondary">
                  {c.fecha ?? "—"} · {c.tipoDocumento ?? "—"} {c.numeroDocumento ?? ""} ·{" "}
                  {c.proveedor?.razonSocial ?? "—"}
                </span>
                <button
                  type="button"
                  onClick={() =>
                    onVincular({
                      idCompra: c.idCompra,
                      fecha: c.fecha,
                      tipoDocumento: c.tipoDocumento,
                      numeroDocumento: c.numeroDocumento,
                    })
                  }
                  className="text-finance hover:underline"
                >
                  Vincular
                </button>
              </li>
            ))}
        </ul>
      )}
      {resultados && busquedaAplicada.length >= 2 && resultados.items.length === 0 && (
        <p className="mt-1 text-xs text-ink-muted">Sin resultados para &quot;{busquedaAplicada}&quot;.</p>
      )}
    </div>
  );
}
