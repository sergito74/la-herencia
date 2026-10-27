"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { formatFecha, formatMoneda } from "@/lib/format";
import { getCargasParaRevisar, marcarRevisado } from "@/services/bovedaApi";
import { urlDocumentoLocal } from "@/services/comprasApi";

/** Compras que el sistema cargó solo, para revisar que hayan quedado bien imputadas (regla 27/10/2026). */
export function RevisionCargas() {
  const qc = useQueryClient();
  const cargas = useQuery({ queryKey: ["boveda", "revision"], queryFn: getCargasParaRevisar });
  const revisar = useMutation({
    mutationFn: marcarRevisado,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["boveda", "revision"] }),
  });

  const items = cargas.data ?? [];
  if (items.length === 0) return null;

  return (
    <section className="space-y-3 rounded-md border border-finance/40 bg-surface p-3">
      <div>
        <h2 className="text-base font-semibold">Cargado solo en Compras — para revisar ({items.length})</h2>
        <p className="text-xs text-ink-secondary">
          Revisá proveedor, rubro, centro de costo e importes. Si algo está mal, corregilo en la compra; cuando esté
          bien, marcala como revisada.
        </p>
      </div>
      {items.map((c) => (
        <div key={c.idDocumento} className="rounded-md border border-border p-3">
          <div className="flex flex-wrap items-baseline justify-between gap-2 text-sm">
            <div>
              <strong>{c.proveedor ?? c.portal}</strong>
              <span className="ml-2 text-ink-secondary">
                {c.tipoDocumento} {c.tipo} {c.numero} · {formatFecha(c.fecha)}
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="font-medium">{c.total == null ? "—" : formatMoneda(c.total, "Pesos")}</span>
              {c.ruta && (
                <a href={urlDocumentoLocal(c.ruta)} target="_blank" rel="noreferrer" className="text-finance hover:underline">
                  Ver PDF
                </a>
              )}
              <Link href={`/compras/${c.idCompra}`} className="text-finance hover:underline">Ver compra</Link>
              <button type="button" disabled={revisar.isPending} onClick={() => revisar.mutate(c.idDocumento)}
                className="rounded-md bg-finance px-3 py-1 text-xs font-medium text-white disabled:opacity-40">
                Revisado
              </button>
            </div>
          </div>
          <table className="mt-2 w-full text-xs">
            <thead>
              <tr className="border-b border-border text-left text-ink-muted">
                <th className="py-1 pr-3">Detalle</th>
                <th className="py-1 pr-3">Rubro</th>
                <th className="py-1 pr-3">Centro de costo</th>
                <th className="py-1 pr-3 text-right">Importe</th>
                <th className="py-1 text-right">IVA</th>
              </tr>
            </thead>
            <tbody>
              {c.renglones.map((r, i) => (
                <tr key={i} className="border-b border-border/50">
                  <td className="py-1 pr-3">{r.detalle}</td>
                  <td className="py-1 pr-3">{r.rubro ?? "—"}</td>
                  <td className="py-1 pr-3">{r.centroCosto ?? "—"}</td>
                  <td className="py-1 pr-3 text-right whitespace-nowrap">
                    {formatMoneda((r.cantidad ?? 1) * (r.precioUnitario ?? 0), "Pesos")}
                  </td>
                  <td className="py-1 text-right">{r.iva ? `${String(r.iva).replace(".", ",")}%` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
      {revisar.isError && <p className="text-sm text-red-700">{revisar.error.message}</p>}
    </section>
  );
}
