"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { formatMoneda } from "@/lib/format";
import { revisionCuentasApi, type Cola, type EstadoEfectivo } from "@/services/revisionCuentasApi";

export const NOMBRE_COLA: Record<Cola, string> = {
  A: "Ya sanas",
  B: "Solo imputación",
  C: "Doble conteo con tarjeta",
  D: "Pago sin factura",
  E: "Contacto duplicado o movimiento sin contacto",
  F: "Dólares y mixtas",
  G: "Retenciones e impuestos",
  H: "Socios, entidades y compras particulares",
  I: "Excepciones",
};

const NOMBRE_ESTADO: Record<EstadoEfectivo, string> = {
  pendiente: "Pendiente",
  "en-proceso": "En proceso",
  "esperando-evidencia": "Esperando evidencia",
  "esperando-sergio": "Esperando a Sergio",
  cerrada: "Cerrada",
  "cerrada-con-excepcion": "Cerrada con excepción",
  reabierta: "Reabierta",
};

const TAMANO = 50;

/** Cuentas de una cola, de las más fáciles (menos movimientos) a las más complejas. Cada cuenta abre su ficha. */
export function ColaCuentas({ cola }: { cola: Cola }) {
  const [pagina, setPagina] = useState(1);
  const { data, isLoading, error } = useQuery({
    queryKey: ["revision-cola", cola, pagina],
    queryFn: () => revisionCuentasApi.cola(cola, pagina, TAMANO),
  });

  if (isLoading) return <p className="text-sm text-ink-secondary">Calculando las cuentas de la cola… (la primera vez puede tardar unos segundos)</p>;
  if (error || !data) return <p role="alert" className="text-sm text-status-danger">No se pudo calcular la cola.</p>;
  const paginas = Math.max(1, Math.ceil(data.total / TAMANO));

  return (
    <section className="text-sm">
      <div className="flex items-baseline justify-between">
        <h2 className="font-semibold">Cola {cola}: {NOMBRE_COLA[cola]}</h2>
        <span className="text-xs text-ink-secondary">{data.total} cuentas · página {pagina} de {paginas}</span>
      </div>
      <p className="text-xs text-ink-secondary">De las más fáciles a las más complejas: menos movimientos primero y, a igual cantidad, menor importe.</p>
      {data.cuentas.length === 0 ? (
        <p className="mt-2 text-ink-secondary">No hay cuentas en esta cola.</p>
      ) : (
        <table className="mt-2 w-full text-xs">
          <thead>
            <tr className="text-left text-ink-secondary">
              <th className="py-1">Cuenta</th>
              <th className="text-right">Movimientos</th>
              <th className="text-right">Importe</th>
              <th className="text-right">Saldo al corte</th>
              <th>Etapa</th>
              <th>Estado</th>
              <th>Otros problemas</th>
            </tr>
          </thead>
          <tbody>
            {data.cuentas.map((c) => (
              <tr key={c.idContacto} className="border-t border-line">
                <td className="py-1">
                  <Link className="text-finance underline" href={`/finanzas/auditoria-cuentas/cuenta/${c.idContacto}`}>{c.razonSocial ?? `Contacto ${c.idContacto}`}</Link>
                </td>
                <td className="text-right">{c.movimientos}</td>
                <td className="text-right">{formatMoneda(c.importe)}</td>
                <td className="text-right">{formatMoneda(c.saldo)}</td>
                <td>{c.etapa}</td>
                <td>{NOMBRE_ESTADO[c.estado]}</td>
                <td>{c.otrosProblemas.length ? c.otrosProblemas.join(", ") : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {paginas > 1 && (
        <div className="mt-2 flex gap-2">
          <button type="button" disabled={pagina <= 1} onClick={() => setPagina(pagina - 1)} className="rounded border border-line px-2 py-0.5 disabled:opacity-40">Anterior</button>
          <button type="button" disabled={pagina >= paginas} onClick={() => setPagina(pagina + 1)} className="rounded border border-line px-2 py-0.5 disabled:opacity-40">Siguiente</button>
        </div>
      )}
    </section>
  );
}
