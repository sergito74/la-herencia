"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { fetchPrimeraPendiente } from "@/services/auditoriaCuentasApi";

/** Entrada al trabajo de todos los días: la primera cuenta sin revisar (alfabético, de las más fáciles a las más complicadas). */
export function EmpezarRevision() {
  const { data } = useQuery({ queryKey: ["auditoria-primera"], queryFn: () => fetchPrimeraPendiente() });
  return (
    <section className="rounded border border-finance p-3 text-sm">
      <h2 className="font-semibold">Revisar cuentas</h2>
      <p className="text-xs text-ink-secondary">Se recorren en orden alfabético, empezando por las más fáciles. En cada cuenta ves los movimientos, corregís lo que no esté bien y la marcás como revisada.</p>
      {data ? (
        <Link className="mt-2 inline-block rounded bg-finance px-3 py-1 text-white" href={`/finanzas/auditoria-cuentas/cuenta/${data.idContacto}`}>
          Empezar con {data.razonSocial}
        </Link>
      ) : (
        <p className="mt-1 text-xs text-status-success">No quedan cuentas pendientes.</p>
      )}
    </section>
  );
}
