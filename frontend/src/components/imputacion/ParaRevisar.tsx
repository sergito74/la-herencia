"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { formatFecha, formatMoneda } from "@/lib/format";
import { apiGet } from "@/services/apiClient";

interface Fila {
  idCompra: number;
  fecha: string;
  proveedor: string | null;
  tipoDocumento: string | null;
  nroDocumento: string | null;
  idDetalleCompra: number;
  producto: string | null;
  importe: number;
  moneda: string | null;
  motivo: string;
}

/** 050 US6: comprobantes cuya imputación espera una decisión. Se resuelven desde la compra (renglón → Cambiar). */
export function ParaRevisar() {
  const { data } = useQuery({ queryKey: ["imputacion-revisar", "lista"], queryFn: () => apiGet<Fila[]>("/api/imputacion/revisar") });
  const filas = data ?? [];
  if (!filas.length) return null;
  const porCompra = new Map<number, Fila[]>();
  filas.forEach((f) => porCompra.set(f.idCompra, [...(porCompra.get(f.idCompra) ?? []), f]));
  return (
    <section id="revisar" className="mt-3 space-y-2 rounded border border-status-warning bg-status-warning-bg p-3">
      <h2 className="text-sm font-semibold">Para revisar ({porCompra.size})</h2>
      <ul className="divide-y rounded border bg-white text-sm">
        {[...porCompra.values()].map((rs) => (
          <li key={rs[0].idCompra} className="space-y-1 p-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span>
                <strong>{rs[0].proveedor}</strong> · {rs[0].tipoDocumento} {rs[0].nroDocumento} del {formatFecha(rs[0].fecha)}
              </span>
              <Link className="text-finance underline" href={`/compras/${rs[0].idCompra}/editar`}>
                Abrir la compra
              </Link>
            </div>
            {rs.map((r) => (
              <p key={r.idDetalleCompra} className="text-xs text-ink-secondary">
                {r.producto} ({formatMoneda(r.importe, r.moneda === "Dolares" ? "Dolares" : "Pesos")}): {r.motivo}
              </p>
            ))}
          </li>
        ))}
      </ul>
    </section>
  );
}
