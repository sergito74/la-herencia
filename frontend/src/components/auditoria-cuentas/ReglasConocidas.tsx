"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { formatMoneda } from "@/lib/format";
import { crearConocido, darDeBajaConocido, fetchConocidos, type Conocido } from "@/services/auditoriaCuentasApi";

export function useRefrescarAuditoria() {
  const qc = useQueryClient();
  return () => {
    for (const k of ["auditoria-resumen", "auditoria-grupo", "auditoria-conocidos", "auditoria-hallazgos"]) qc.invalidateQueries({ queryKey: [k] });
  };
}

/** Formulario chico: una regla nueva con su motivo (concepto de movimiento o diferencia de una cuenta). */
export function NuevaRegla({
  tipo, claveInicial, importeRef, etiqueta, onListo,
}: { tipo: Conocido["tipo"]; claveInicial: string; importeRef?: number; etiqueta: string; onListo?: () => void }) {
  const refrescar = useRefrescarAuditoria();
  const [abierto, setAbierto] = useState(false);
  const [clave, setClave] = useState(claveInicial);
  const [motivo, setMotivo] = useState("");
  const [error, setError] = useState<string | null>(null);
  const crear = useMutation({
    mutationFn: () => crearConocido({ tipo, clave, motivo, importeRef }),
    onSuccess: () => {
      setAbierto(false);
      setError(null);
      refrescar();
      onListo?.();
    },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : "No se pudo guardar la regla."),
  });
  return (
    <SoloLectura>
      {!abierto ? (
        <button type="button" onClick={() => setAbierto(true)} className="rounded border border-line px-2 py-0.5 text-xs">
          {etiqueta}
        </button>
      ) : (
        <span className="inline-flex flex-wrap items-center gap-1 text-xs">
          {tipo === "concepto-movimiento" && (
            <input value={clave} onChange={(e) => setClave(e.target.value)} aria-label="Texto del concepto" className="w-48 rounded border border-line px-1 py-0.5" />
          )}
          <input value={motivo} onChange={(e) => setMotivo(e.target.value)} placeholder="Motivo (obligatorio)" aria-label="Motivo" className="w-56 rounded border border-line px-1 py-0.5" />
          <button type="button" disabled={crear.isPending || !motivo.trim()} onClick={() => crear.mutate()} className="rounded bg-finance px-2 py-0.5 text-white">
            Guardar
          </button>
          <button type="button" onClick={() => setAbierto(false)} className="rounded border border-line px-2 py-0.5">Cancelar</button>
          {error && <span role="alert" className="text-status-danger">{error}</span>}
        </span>
      )}
    </SoloLectura>
  );
}

/** Lo que ya se dio por conocido (conceptos de movimientos y diferencias documentadas), con baja. */
export function ReglasConocidas() {
  const refrescar = useRefrescarAuditoria();
  const { data } = useQuery({ queryKey: ["auditoria-conocidos"], queryFn: fetchConocidos });
  const baja = useMutation({ mutationFn: (id: number) => darDeBajaConocido(id), onSuccess: refrescar });
  const lista = data ?? [];
  return (
    <section className="text-xs">
      <h2 className="text-sm font-semibold">Lo que ya se dio por conocido</h2>
      <p className="text-ink-secondary">Reglas que explican movimientos sin contacto (de cualquier monto) y diferencias de cuentas ya documentadas. Se pueden dar de baja.</p>
      <ul className="mt-1 divide-y divide-line">
        {lista.map((k) => (
          <li key={k.idConocido} className="flex items-center gap-2 py-1">
            <span>
              {k.tipo === "cuenta" ? `Cuenta ${k.clave}` : k.tipo === "tc-pactado" ? `Cuenta ${k.clave}: tipo de cambio pactado` : `Concepto «${k.clave}»`} — {k.motivo}
              {k.importeRef != null && ` (diferencia documentada ${formatMoneda(k.importeRef)})`}
            </span>
            <SoloLectura>
              <button type="button" onClick={() => baja.mutate(k.idConocido)} className="rounded border border-line px-2 py-0.5">Dar de baja</button>
            </SoloLectura>
          </li>
        ))}
        {lista.length === 0 && <li className="py-1 text-ink-secondary">Todavía no hay reglas.</li>}
      </ul>
    </section>
  );
}
