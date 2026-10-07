"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Fragment, useState } from "react";

import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatFecha, formatMoneda } from "@/lib/format";

import { AsignarContacto } from "./AsignarContacto";
import { NuevaRegla } from "./ReglasConocidas";
import { fetchGrupo, fetchHallazgos, type CausaCuenta, type CuentaAuditada } from "@/services/auditoriaCuentasApi";

function Detalle({ cuenta }: { cuenta: CuentaAuditada }) {
  const { data, isLoading } = useQuery({
    queryKey: ["auditoria-hallazgos", cuenta.idContacto],
    queryFn: () => fetchHallazgos(cuenta.idContacto),
  });
  if (isLoading) return <LoadingState />;
  return (
    <ul className="space-y-1 pl-4 text-xs text-ink-secondary">
      {(data?.hallazgos ?? []).map((h, i) => (
        <li key={i}>
          {h.motivo}
          {h.importe != null && <b className="ml-2 text-ink-primary">{formatMoneda(h.importe)}</b>}
          {h.medio && h.idMovimiento && (
            <Link className="ml-2 text-finance underline" href={`/finanzas/tesoreria?medio=${h.medio}&highlight=${h.idMovimiento}`}>
              ver el movimiento {h.idMovimiento}
            </Link>
          )}
          {h.cantidadFacturas != null && (
            <span className="ml-2">
              · {h.cantidadFacturas} facturas, la más vieja del {formatFecha(h.facturaMasVieja)}
              {h.fechaPago ? `, pago del ${formatFecha(h.fechaPago)}` : ""}
              {h.diasMaximos != null ? ` (hasta ${h.diasMaximos} días)` : ""}
            </span>
          )}
        </li>
      ))}
      {(data?.hallazgos ?? []).length === 0 && <li>Sin hallazgos para mostrar.</li>}
    </ul>
  );
}

/** Cuentas de un grupo de causa, con saldo del sistema, del Access y diferencia (035, FR-003). */
export function GrupoExcepciones({ causa, titulo }: { causa: CausaCuenta; titulo: string }) {
  const [abierta, setAbierta] = useState<number | null>(null);
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["auditoria-grupo", causa],
    queryFn: () => fetchGrupo(causa),
  });
  if (isLoading) return <LoadingState />;
  if (isError || !data) return <ErrorState message="No se pudo cargar el grupo." onRetry={() => refetch()} />;

  return (
    <section className="space-y-1">
      <h3 className="text-sm font-semibold">
        {titulo} <span className="text-ink-secondary">({data.total})</span>
      </h3>
      {data.conceptos && data.conceptos.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs text-ink-secondary">
            Movimientos del banco sin contacto, de cualquier monto, agrupados por concepto. Una regla por grupo los da por explicados.
          </p>
          <ul className="space-y-2 text-xs">
            {data.conceptos.map((g) => (
              <li key={g.concepto} className="rounded border border-line p-2">
                <div className="flex flex-wrap items-center gap-2">
                  <b>{g.concepto}</b>
                  <span>{g.movimientos} movimientos · {formatMoneda(g.importe)}</span>
                  <NuevaRegla tipo="concepto-movimiento" claveInicial={g.concepto} etiqueta="Dar por explicado" />
                  <AsignarContacto concepto={g.concepto} />
                </div>
                <ul className="mt-1 text-ink-secondary">
                  {g.ejemplos.map((m) => (
                    <li key={`${m.medio}-${m.idMovimiento}`}>
                      {formatFecha(m.fecha)} · {formatMoneda(m.importe)}
                      <Link className="ml-2 text-finance underline" href={`/finanzas/tesoreria?medio=${m.medio}&highlight=${m.idMovimiento}`}>ver el movimiento</Link>
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </div>
      )}
      {data.explicados && data.explicados.length > 0 && (
        <p className="text-xs text-ink-secondary">
          Ya explicados por reglas: {data.explicados.map((e) => `${e.clave} (${e.movimientos})`).join(", ")}.
        </p>
      )}
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-ink-secondary">
            <th className="py-1">Cuenta</th>
            <th className="text-right">Saldo del sistema</th>
            <th className="text-right">Saldo del Access</th>
            <th className="text-right">Diferencia</th>
            <th className="text-right">Sin explicar</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((c) => (
            <Fragment key={c.idContacto}>
              <tr className="border-t border-line">
                <td className="py-1">
                  <button type="button" className="mr-2 text-xs underline" onClick={() => setAbierta(abierta === c.idContacto ? null : c.idContacto)}>
                    {abierta === c.idContacto ? "Cerrar" : "Ver causas"}
                  </button>
                  <Link className="text-finance underline" href={`/finanzas/auditoria-cuentas/cuenta/${c.idContacto}`}>
                    {c.razonSocial ?? `Contacto ${c.idContacto}`}
                  </Link>
                  {c.moneda === "Dolares" && <span className="ml-1 text-xs text-ink-secondary">(en dólares)</span>}
                  {c.documentada && <span className="ml-1 text-xs text-ink-secondary">· documentada: {c.documentada}</span>}
                  {causa === "otros" && c.diferencia != null && (
                    <span className="ml-2">
                      <NuevaRegla tipo="cuenta" claveInicial={String(c.idContacto)} importeRef={c.diferencia} etiqueta="Documentar esta diferencia" />
                    </span>
                  )}
                </td>
                <td className="text-right">{formatMoneda(c.saldoSistema, c.moneda === "Dolares" ? "Dolares" : "Pesos")}</td>
                <td className="text-right">{c.saldoAccess != null ? formatMoneda(c.saldoAccess, c.moneda === "Dolares" ? "Dolares" : "Pesos") : "—"}</td>
                <td className="text-right">{c.diferencia != null ? formatMoneda(c.diferencia, c.moneda === "Dolares" ? "Dolares" : "Pesos") : "—"}</td>
                <td className="text-right">{formatMoneda(c.sinExplicar, c.moneda === "Dolares" ? "Dolares" : "Pesos")}</td>
              </tr>
              {abierta === c.idContacto && (
                <tr>
                  <td colSpan={5} className="pb-2">
                    <Detalle cuenta={c} />
                  </td>
                </tr>
              )}
            </Fragment>
          ))}
        </tbody>
      </table>
    </section>
  );
}
