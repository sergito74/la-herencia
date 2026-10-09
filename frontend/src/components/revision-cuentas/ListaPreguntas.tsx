"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { formatFecha } from "@/lib/format";
import { revisionCuentasApi } from "@/services/revisionCuentasApi";
import { NOMBRE_COLA } from "./ColaCuentas";

/** Preguntas que bloquean cuentas: una por cuenta, con lo que hace falta para seguir. Cada una abre la ficha de su cuenta. */
export function ListaPreguntas() {
  const { data, isLoading, error } = useQuery({ queryKey: ["revision-preguntas"], queryFn: () => revisionCuentasApi.preguntas() });

  return (
    <section>
      <h2 className="mb-1 font-semibold">Preguntas que bloquean cuentas</h2>
      {isLoading && <p className="text-xs text-ink-secondary">Buscando preguntas…</p>}
      {error && <p role="alert" className="text-xs text-status-danger">No se pudieron cargar las preguntas.</p>}
      {data && data.length === 0 && <p className="text-xs text-status-success">No hay preguntas pendientes: ninguna cuenta espera una decisión de Sergio.</p>}
      {data && data.length > 0 && (
        <ul className="space-y-1 text-xs">
          {data.map((p) => (
            <li key={p.idContacto} className="rounded border border-line p-2">
              <Link className="font-medium text-finance underline" href={`/finanzas/auditoria-cuentas/cuenta/${p.idContacto}`}>{p.razonSocial ?? `Contacto ${p.idContacto}`}</Link>
              <span className="ml-2 text-ink-secondary">Cola {p.cola}: {NOMBRE_COLA[p.cola]} · {p.etapa}{p.desde ? ` · desde el ${formatFecha(p.desde)}` : ""}</span>
              <p>{p.pregunta}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
