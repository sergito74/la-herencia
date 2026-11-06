"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo, useState } from "react";

import { BackLink } from "@/components/ui/BackLink";
import { filterInputClass } from "@/components/ui/FilterBar";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatCantidad, formatFecha, formatMoneda } from "@/lib/format";
import { fetchFacturasSinOrden, urlExportarFacturasSinOrden, type RenglonSinOrden } from "@/services/ordenesApi";

/** 048 FR-008: facturas de labor de contratistas sin orden de trabajo. Su costo sigue contando por la imputación
 *  cargada a mano; para que se impute sola, abrí la factura y tildá sus órdenes. */
export default function FacturasSinOrdenPage() {
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["facturas-sin-orden"], queryFn: fetchFacturasSinOrden, staleTime: 0 });
  const [contratista, setContratista] = useState("");

  const facturas = useMemo(() => {
    const porFactura = new Map<number, RenglonSinOrden[]>();
    for (const r of data ?? []) {
      if (contratista && r.contratista !== contratista) continue;
      porFactura.set(r.idCompra, [...(porFactura.get(r.idCompra) ?? []), r]);
    }
    return [...porFactura.values()];
  }, [data, contratista]);
  const contratistas = useMemo(() => [...new Set((data ?? []).map((r) => r.contratista))].sort(), [data]);

  return (
    <main className="mx-auto max-w-6xl space-y-4 p-4">
      <BackLink href="/produccion/ordenes">Volver a Órdenes de trabajo</BackLink>
      <h1 className="text-xl font-semibold">Facturas de contratistas sin orden de trabajo</h1>
      <p className="text-sm text-ink-secondary">
        Su costo cuenta por el cultivo y la campaña cargados a mano en cada renglón. Para que se impute solo por la
        superficie de la orden, abrí la factura y tildá sus órdenes de trabajo.
      </p>
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm">
          Contratista
          <select className={filterInputClass} value={contratista} onChange={(e) => setContratista(e.target.value)}>
            <option value="">Todos</option>
            {contratistas.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </label>
        <a href={urlExportarFacturasSinOrden()} className="rounded border border-border px-3 py-1.5 text-sm">
          Exportar a Excel
        </a>
        {data && <span className="text-sm text-ink-secondary">{facturas.length} facturas</span>}
      </div>
      {isLoading && <LoadingState />}
      {isError && <ErrorState message="No se pudieron cargar las facturas." onRetry={() => refetch()} />}
      {data && facturas.length === 0 && <p className="text-sm text-ink-secondary">No hay facturas de contratistas sin orden.</p>}
      {facturas.length > 0 && (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-ink-secondary">
              <th className="py-1">Factura</th>
              <th className="py-1">Rubro</th>
              <th className="py-1">Concepto</th>
              <th className="py-1 text-right">Cantidad</th>
              <th className="py-1 text-right">Neto</th>
              <th className="py-1">Cultivo / campaña (a mano)</th>
            </tr>
          </thead>
          <tbody>
            {facturas.map((renglones) =>
              renglones.map((r, i) => (
                <tr key={`${r.idCompra}-${i}`} className={i === 0 ? "border-t border-border align-top" : "align-top"}>
                  <td className="py-1">
                    {i === 0 && (
                      <Link href={`/compras/${r.idCompra}/editar`} className="text-finance hover:underline">
                        {r.contratista} · {r.numero} · {formatFecha(r.fecha)}
                      </Link>
                    )}
                  </td>
                  <td className="py-1">{r.rubro ?? ""}</td>
                  <td className="py-1">{r.concepto ?? ""}</td>
                  <td className="py-1 text-right">
                    {r.cantidad != null ? formatCantidad(r.cantidad) : ""} {r.unidad ?? ""}
                  </td>
                  <td className="py-1 text-right">{formatMoneda(r.neto, r.moneda === "Dolares" ? "Dolares" : "Pesos")}</td>
                  <td className="py-1">
                    {r.destino ?? "(sin imputar)"} · {r.campania ?? "(sin imputar)"}
                  </td>
                </tr>
              )),
            )}
          </tbody>
        </table>
      )}
    </main>
  );
}
