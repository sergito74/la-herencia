"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { formatMoneda, parseNumeroLocal } from "@/lib/format";
import { revisionCuentasApi, type Cola, type Lote } from "@/services/revisionCuentasApi";

/**
 * Lote de una cola: se elige la regla, se simula (no cambia nada), se tildan las cuentas (nada viene tildado de antemano) y se aplica con
 * respaldo. Un lote aplicado se puede revertir. Solo se tildan las cuentas que cumplen la regla.
 */
export function LoteCola({ cola }: { cola: Cola }) {
  const qc = useQueryClient();
  const { data: reglas } = useQuery({ queryKey: ["revision-reglas"], queryFn: () => revisionCuentasApi.reglas() });
  const regla = (reglas ?? []).find((r) => r.cola === cola);
  const [lote, setLote] = useState<Lote | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmar, setConfirmar] = useState(false);
  const [tope, setTope] = useState("");
  const alFallar = (e: unknown) => setError(e instanceof Error ? e.message : "No se pudo completar.");
  const refrescar = () => {
    for (const k of ["revision-cola", "revision-tablero", "revision-ficha"]) qc.invalidateQueries({ queryKey: [k] });
  };
  const simular = useMutation({
    mutationFn: () => revisionCuentasApi.simularLote(cola, regla!.regla),
    onSuccess: (l) => { setLote(l); setError(null); setConfirmar(false); },
    onError: alFallar,
  });
  const tildar = useMutation({
    mutationFn: (cuerpo: { idsContacto: number[] } | { tildarTodas: true }) => revisionCuentasApi.tildarLote(lote!.idCorreccion, cuerpo),
    onSuccess: (l) => { setLote(l); setError(null); },
    onError: alFallar,
  });
  const aplicar = useMutation({
    mutationFn: () => revisionCuentasApi.aplicarLote(lote!.idCorreccion),
    onSuccess: (l) => { setLote(l); setError(null); setConfirmar(false); refrescar(); },
    onError: alFallar,
  });
  const revertir = useMutation({
    mutationFn: () => revisionCuentasApi.revertirLote(lote!.idCorreccion),
    onSuccess: (l) => { setLote(l); setError(null); refrescar(); },
    onError: alFallar,
  });
  const descartar = useMutation({
    mutationFn: () => revisionCuentasApi.descartarLote(lote!.idCorreccion),
    onSuccess: () => { setLote(null); setError(null); },
    onError: alFallar,
  });

  if (!regla) {
    return <p className="text-xs text-ink-secondary">Esta cola no tiene una regla de lote: sus cuentas se resuelven con las herramientas de cada una.</p>;
  }
  const tildadas = lote?.cuentas.filter((c) => c.tildada) ?? [];
  const simulado = lote?.estado === "simulada";

  const alternar = (id: number) => {
    if (!lote) return;
    const ids = new Set(tildadas.map((c) => c.idContacto));
    if (ids.has(id)) ids.delete(id); else ids.add(id);
    tildar.mutate({ idsContacto: [...ids] });
  };

  return (
    <SoloLectura>
      <section className="rounded border border-line p-3 text-xs">
        <h2 className="text-sm font-semibold">Lote de la cola {cola}</h2>
        <p className="text-ink-secondary">Regla: {regla.descripcion}.</p>
        {!lote && (
          <button type="button" disabled={simular.isPending} onClick={() => simular.mutate()} className="mt-2 rounded border border-line px-3 py-1">
            {simular.isPending ? "Calculando…" : "Armar el lote (no cambia nada)"}
          </button>
        )}
        {error && <p role="alert" className="mt-1 text-status-danger">{error}</p>}
        {lote && (
          <div className="mt-2 space-y-2">
            <p>
              Lote <b>#{lote.idCorreccion}</b> · {lote.estado === "simulada" ? "simulado" : lote.estado} · {lote.cuentas.length} cuentas, {lote.cuentas.filter((c) => c.cumple).length} cumplen la regla,{" "}
              {tildadas.length} tildadas
              {lote.respaldo ? <> · respaldo: {lote.respaldo}</> : null}
            </p>
            {simulado && (
              <div className="flex flex-wrap gap-2">
                <button type="button" disabled={tildar.isPending} onClick={() => tildar.mutate({ tildarTodas: true })} className="rounded border border-line px-3 py-1">
                  Tildar todas las que cumplen
                </button>
                <button type="button" disabled={tildar.isPending || tildadas.length === 0} onClick={() => tildar.mutate({ idsContacto: [] })} className="rounded border border-line px-3 py-1">
                  Desmarcar todas
                </button>
                <span className="flex items-center gap-1">
                  <label>
                    Tildar solo las de saldo hasta ${" "}
                    <input inputMode="decimal" value={tope} onChange={(e) => setTope(e.target.value)} placeholder="por ejemplo 10.000" className="w-28 rounded border border-line px-1 py-0.5" aria-label="Saldo máximo para tildar" />
                  </label>
                  <button
                    type="button"
                    disabled={tildar.isPending || !tope.trim()}
                    onClick={() => {
                      const max = Math.abs(parseNumeroLocal(tope));
                      tildar.mutate({ idsContacto: lote.cuentas.filter((c) => c.cumple && Math.abs(c.saldoAntes ?? 0) <= max).map((c) => c.idContacto) });
                    }}
                    className="rounded border border-line px-3 py-1"
                  >
                    Tildar ese tramo
                  </button>
                </span>
                <button type="button" disabled={tildadas.length === 0} onClick={() => setConfirmar(true)} className="rounded bg-finance px-3 py-1 text-white disabled:opacity-40">
                  Aplicar a las tildadas
                </button>
                <button type="button" disabled={descartar.isPending} onClick={() => descartar.mutate()} className="rounded border border-line px-3 py-1">
                  Descartar el lote
                </button>
              </div>
            )}
            {confirmar && simulado && (
              <p className="rounded border border-line p-2">
                ¿Aplicar la regla a las {tildadas.length} cuentas tildadas? Se hace un respaldo antes y se puede revertir.{" "}
                <button type="button" disabled={aplicar.isPending} onClick={() => aplicar.mutate()} className="rounded bg-finance px-3 py-1 text-white">
                  {aplicar.isPending ? "Aplicando…" : "Sí, aplicar"}
                </button>{" "}
                <button type="button" onClick={() => setConfirmar(false)} className="rounded border border-line px-2 py-0.5">No</button>
              </p>
            )}
            {lote.estado === "aplicada" && (
              <p className="text-status-success">
                Lote aplicado.{" "}
                <button type="button" disabled={revertir.isPending} onClick={() => revertir.mutate()} className="ml-2 rounded border border-line px-2 py-0.5">
                  Revertir el lote
                </button>
              </p>
            )}
            {lote.estado === "revertida" && <p className="text-ink-secondary">Lote revertido: las cuentas volvieron a su estado anterior.</p>}
            <table className="w-full">
              <thead>
                <tr className="text-left text-ink-secondary">
                  <th className="w-8"></th>
                  <th>Cuenta</th>
                  <th className="text-right">Saldo antes</th>
                  <th className="text-right">Saldo después</th>
                  <th>Detalle</th>
                </tr>
              </thead>
              <tbody>
                {lote.cuentas.map((c) => (
                  <tr key={c.idContacto} className={`border-t border-line ${c.cumple ? "" : "text-ink-secondary"}`}>
                    <td>
                      <input type="checkbox" aria-label={`Tildar ${c.razonSocial ?? c.idContacto}`} checked={c.tildada} disabled={!simulado || !c.cumple || tildar.isPending} onChange={() => alternar(c.idContacto)} />
                    </td>
                    <td>
                      <Link className="text-finance underline" href={`/finanzas/auditoria-cuentas/cuenta/${c.idContacto}`}>{c.razonSocial ?? `Contacto ${c.idContacto}`}</Link>
                    </td>
                    <td className="text-right">{c.saldoAntes === null ? "—" : formatMoneda(c.saldoAntes)}</td>
                    <td className="text-right">{c.saldoDespues === null ? "—" : formatMoneda(c.saldoDespues)}</td>
                    <td>{c.detalle || (c.cumple ? "Cumple la regla" : "No cumple")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </SoloLectura>
  );
}
