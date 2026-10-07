"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatFecha, formatMoneda } from "@/lib/format";
import { asignarContacto, fetchMovimientosSinContacto } from "@/services/auditoriaCuentasApi";

/** Asigna un contacto a movimientos del banco que no lo tienen: tildando uno, varios o todos los de un concepto (la regla). Se puede deshacer desde la cuenta del contacto. */
export function AsignarContacto({ concepto }: { concepto: string }) {
  const qc = useQueryClient();
  const [abierto, setAbierto] = useState(false);
  const [tildados, setTildados] = useState<Set<string> | null>(null);
  const [contacto, setContacto] = useState<{ id: number; nombre: string | null } | null>(null);
  const [motivo, setMotivo] = useState("");
  const [hecho, setHecho] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["auditoria-sin-contacto", concepto],
    queryFn: () => fetchMovimientosSinContacto(concepto),
    enabled: abierto,
  });
  const clave = (m: { medio: string; idMovimiento: number }) => `${m.medio}-${m.idMovimiento}`;
  const elegidos = tildados ?? new Set((data ?? []).map(clave));
  const asignar = useMutation({
    mutationFn: () =>
      asignarContacto((data ?? []).filter((m) => elegidos.has(clave(m))).map((m) => ({ medio: m.medio, idMovimiento: m.idMovimiento })), contacto!.id, motivo),
    onSuccess: (r) => {
      setHecho(`Se asignaron ${r.movimientos} movimientos a ${r.contacto}. Podés deshacerlo desde la cuenta de ese contacto.`);
      setAbierto(false);
      setTildados(null);
      setError(null);
      for (const k of ["auditoria-resumen", "auditoria-grupo", "auditoria-sin-contacto", "auditoria-revision"]) qc.invalidateQueries({ queryKey: [k] });
    },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : "No se pudo asignar."),
  });

  return (
    <SoloLectura>
      {hecho && <span className="text-xs text-status-success">{hecho}</span>}
      {!abierto ? (
        <button type="button" onClick={() => { setAbierto(true); setHecho(null); }} className="rounded border border-line px-2 py-0.5 text-xs">Asignar contacto…</button>
      ) : (
        <div className="mt-1 w-full space-y-2 rounded border border-finance p-2 text-xs">
          {isLoading && <LoadingState />}
          {isError && <ErrorState message="No se pudieron cargar los movimientos." onRetry={() => refetch()} />}
          {data && (
            <>
              <p className="text-ink-secondary">
                Tildá los movimientos que son de un mismo contacto. Vienen todos tildados: es la regla de este concepto. {elegidos.size} de {data.length} elegidos.
              </p>
              <ul className="max-h-48 overflow-auto">
                {data.map((m) => (
                  <li key={clave(m)} className="flex items-center gap-2 py-0.5">
                    <input
                      type="checkbox"
                      aria-label={`Movimiento ${m.idMovimiento}`}
                      checked={elegidos.has(clave(m))}
                      onChange={(e) => {
                        const siguiente = new Set(elegidos);
                        if (e.target.checked) siguiente.add(clave(m));
                        else siguiente.delete(clave(m));
                        setTildados(siguiente);
                      }}
                    />
                    <span>{formatFecha(m.fecha)} · {formatMoneda(m.importe)} · {m.medio} · {m.concepto}</span>
                    <Link className="text-finance underline" href={`/finanzas/tesoreria?medio=${m.medio}&highlight=${m.idMovimiento}`}>ver</Link>
                  </li>
                ))}
              </ul>
              <div className="flex flex-wrap items-end gap-2">
                <div className="w-64">
                  <ContactoSelect value={contacto?.id ?? null} razonSocial={contacto?.nombre} onChange={(id, nombre) => setContacto(id ? { id, nombre } : null)} placeholder="Contacto…" />
                </div>
                <input value={motivo} onChange={(e) => setMotivo(e.target.value)} placeholder="Motivo (obligatorio)" aria-label="Motivo de la asignación" className="w-64 rounded border border-line px-2 py-1" />
                <button type="button" disabled={asignar.isPending || !contacto || !motivo.trim() || elegidos.size === 0} onClick={() => asignar.mutate()} className="rounded bg-finance px-3 py-1 text-white">
                  Asignar {elegidos.size} movimientos
                </button>
                <button type="button" onClick={() => setAbierto(false)} className="rounded border border-line px-3 py-1">Cancelar</button>
              </div>
              {error && <p role="alert" className="text-status-danger">{error}</p>}
            </>
          )}
        </div>
      )}
    </SoloLectura>
  );
}
