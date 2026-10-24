"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { formatFecha, formatMoneda } from "@/lib/format";
import { fetchControlBanco } from "@/services/cuentasSociosApi";

const MEDIO: Record<string, string> = { "Banco Nacion": "bna", Galicia: "galicia", "Mercado Pago": "mercado-libre" };

/** La cuenta de socio es la oficial; el contacto solo marca los movimientos de banco. Este control muestra los
 * movimientos de banco del socio que todavía no tienen su asiento (mismo importe, ±5 días). */
export function ControlBancoSocio({ idSocio }: { idSocio: number }) {
  const q = useQuery({ queryKey: ["cuenta-socio", idSocio, "control-banco"], queryFn: () => fetchControlBanco(idSocio) });
  const [abierto, setAbierto] = useState(false);
  const d = q.data;
  if (!d || d.idContacto == null) return null;
  const ok = d.sinAsiento.length === 0;
  return (
    <section className={`rounded-md border p-3 text-sm ${ok ? "border-border bg-surface" : "border-status-warning bg-status-warning-bg"}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p>
          <strong>Control con el banco:</strong> {d.conAsiento} de {d.banco} movimientos de banco marcados con este socio tienen su asiento
          {ok ? " — todo conciliado." : <>; <strong>{d.sinAsiento.length} sin asiento</strong> por {formatMoneda(d.sinAsiento.reduce((s, x) => s + x.importe, 0))}.</>}
        </p>
        {!ok && <button className="underline" onClick={() => setAbierto((v) => !v)}>{abierto ? "Ocultar" : "Ver cuáles"}</button>}
      </div>
      {abierto && (
        <table className="mt-2 min-w-full">
          <thead className="text-left text-xs uppercase text-ink-secondary">
            <tr><th className="py-1">Fecha</th><th>Banco</th><th>Sentido</th><th className="text-right">Importe</th><th /></tr>
          </thead>
          <tbody className="divide-y divide-border">
            {d.sinAsiento.map((x) => (
              <tr key={`${x.origen}-${x.idOrigen}`}>
                <td className="py-1">{formatFecha(x.fecha)}</td>
                <td>{x.origen}</td>
                <td>{x.sentido}</td>
                <td className="font-data text-right tabular-nums">{formatMoneda(x.importe)}</td>
                <td className="pl-3">
                  {MEDIO[x.origen] && <a className="underline" href={`/finanzas/tesoreria?medio=${MEDIO[x.origen]}&highlight=${x.idOrigen}`}>Ver en el banco</a>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="mt-1 text-xs text-ink-secondary">
        Cargá el asiento que falta con «+ Nuevo asiento» (ingreso a Giamigli = Haber del socio; egreso = Debe), o corregí el contacto del movimiento si no es del socio.
      </p>
    </section>
  );
}
