"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Fragment, useState } from "react";

import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatNumero } from "@/lib/format";
import { fetchCostoPorParte } from "@/services/resultadoCultivoApi";

import { ar, celdaNum, us } from "./FormularioAccess";

/** 050 US7: costo del cultivo agrupado en las partes de la estructura, con $/ha y US$/ha y apertura al documento. */
export function CostoPorParte({ idCultivo, idCampania }: { idCultivo: number; idCampania: number }) {
  const [abierta, setAbierta] = useState<string | null>(null);
  const { data: d, isLoading, isError, refetch } = useQuery({
    queryKey: ["costo-por-parte", idCampania, idCultivo],
    queryFn: () => fetchCostoPorParte(idCampania, idCultivo),
  });
  if (isLoading) return <LoadingState />;
  if (isError || !d) return <ErrorState message="No se pudo calcular el costo por parte." onRetry={refetch} />;
  const totalPesos = d.partes.reduce((s, p) => s + p.pesos, 0);
  const totalDolares = d.partes.reduce((s, p) => s + p.dolares, 0);
  const ha = d.superficieHa > 0 ? d.superficieHa : null;

  return (
    <section className="mt-4 rounded-md border border-border bg-surface">
      <h3 className="border-b border-border bg-surface-sunken px-3 py-1.5 text-sm font-semibold">
        Costo por parte de la estructura
        <span className="ml-2 font-normal text-ink-muted">{ha ? `${formatNumero(ha, { max: 2 })} ha sembradas` : "sin superficie sembrada"}</span>
      </h3>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-ink-muted">
            <th className="px-2 py-1 text-left font-medium">Parte</th>
            <th className="px-2 py-1 text-right font-medium">Pesos</th>
            <th className="px-2 py-1 text-right font-medium">$/ha</th>
            <th className="px-2 py-1 text-right font-medium">Dólares</th>
            <th className="px-2 py-1 text-right font-medium">US$/ha</th>
          </tr>
        </thead>
        <tbody>
          {d.partes.map((p) => (
            <Fragment key={p.parte}>
              <tr className="cursor-pointer border-b border-border hover:bg-surface-sunken"
                  onClick={() => setAbierta(abierta === p.parte ? null : p.parte)}>
                <td className="px-2 py-1">
                  <span className="mr-1 text-ink-muted">{abierta === p.parte ? "▾" : "▸"}</span>{p.parte}
                </td>
                <td className={celdaNum}>{ar(p.pesos)}</td>
                <td className={celdaNum}>{ar(p.pesosHa)}</td>
                <td className={celdaNum}>{us(p.dolares)}</td>
                <td className={celdaNum}>{us(p.dolaresHa)}</td>
              </tr>
              {abierta === p.parte && p.documentos.map((doc, i) => (
                <tr key={i} className="border-b border-border bg-surface-sunken text-xs">
                  <td className="py-1 pl-8 pr-2">
                    {doc.idCompra ? (
                      <Link className="text-finance underline" href={`/compras/${doc.idCompra}/editar`}>{doc.rubro ?? doc.concepto ?? "Compra"}</Link>
                    ) : doc.idOrdenTrabajo ? (
                      <Link className="text-finance underline" href={`/produccion/ordenes/${doc.idOrdenTrabajo}`}>
                        {doc.concepto ?? "Orden"} · orden {doc.idOrdenTrabajo}
                      </Link>
                    ) : (doc.rubro ?? doc.concepto ?? "—")}
                  </td>
                  <td className={celdaNum}>{ar(doc.montoPesos)}</td>
                  <td />
                  <td className={celdaNum}>{us(doc.montoDolares)}</td>
                  <td />
                </tr>
              ))}
            </Fragment>
          ))}
          <tr className="bg-surface-sunken font-semibold">
            <td className="px-2 py-1">Total</td>
            <td className={celdaNum}>{ar(totalPesos)}</td>
            <td className={celdaNum}>{ha ? ar(totalPesos / ha) : "—"}</td>
            <td className={celdaNum}>{us(totalDolares)}</td>
            <td className={celdaNum}>{ha ? us(totalDolares / ha) : "—"}</td>
          </tr>
        </tbody>
      </table>
      {(d.enStockSinConsumir.pesos !== 0 || d.estructuraCampania.pesos !== 0) && (
        <div className="space-y-0.5 border-t border-border px-3 py-2 text-xs text-ink-muted">
          {d.enStockSinConsumir.pesos !== 0 && <p>En stock sin consumir (todavía no es costo): {ar(d.enStockSinConsumir.pesos)}</p>}
          {d.estructuraCampania.pesos !== 0 && <p>Gasto general del año agrícola: {ar(d.estructuraCampania.pesos)}</p>}
        </div>
      )}
    </section>
  );
}
