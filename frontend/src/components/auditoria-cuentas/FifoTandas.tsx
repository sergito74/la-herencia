"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatFecha, formatMoneda } from "@/lib/format";
import { aplicarTanda, fetchPlanFifo, revertirTanda, simularTanda, type SimulacionTanda, type Tanda } from "@/services/auditoriaCuentasApi";

const ESTADO: Record<Tanda["estado"], string> = { pendiente: "Pendiente", parcial: "Aplicada en parte", aplicada: "Aplicada" };

function UnaTanda({ tanda }: { tanda: Tanda }) {
  const qc = useQueryClient();
  const [abierta, setAbierta] = useState(false);
  const [sim, setSim] = useState<SimulacionTanda | null>(null);
  const [aplicada, setAplicada] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const ids = tanda.contactos.map((c) => c.idContacto);
  // la puerta del FIFO deja afuera las cuentas que todavía no completaron E1 a E4: solo se aplica lo que se simuló
  const omitidas = sim?.omitidas ?? [];
  const idsSimulados = ids.filter((i) => !omitidas.some((o) => o.idContacto === i));
  const refrescar = () => {
    for (const k of ["auditoria-fifo-plan", "auditoria-resumen", "auditoria-revision", "auditoria-hallazgos", "auditoria-grupo"]) qc.invalidateQueries({ queryKey: [k] });
  };
  const fallo = (e: unknown) => setError(e instanceof Error ? e.message : "No se pudo completar.");
  const simular = useMutation({ mutationFn: () => simularTanda(ids), onSuccess: (r) => { setSim(r); setAplicada(false); setError(null); }, onError: fallo });
  const aplicar = useMutation({ mutationFn: () => aplicarTanda(sim!.idEjecucion, idsSimulados), onSuccess: () => { setAplicada(true); setError(null); refrescar(); }, onError: fallo });
  const deshacer = useMutation({ mutationFn: () => revertirTanda(sim!.idEjecucion), onSuccess: () => { setAplicada(false); setSim(null); setError(null); refrescar(); }, onError: fallo });
  const r = sim?.resumen;

  return (
    <li className="rounded border border-line p-2 text-xs">
      <div className="flex flex-wrap items-center gap-2">
        <b>Tanda {tanda.numero}</b>
        <span>{tanda.rango} ({tanda.parte})</span>
        <span className="text-ink-secondary">{tanda.contactos.length} cuentas: de {tanda.desde} a {tanda.hasta}</span>
        <span className={tanda.estado === "aplicada" ? "text-status-success" : "text-ink-secondary"}>{ESTADO[tanda.estado]}{tanda.estado === "parcial" ? ` (${tanda.aplicados})` : ""}</span>
        <button type="button" onClick={() => setAbierta(!abierta)} className="underline">{abierta ? "Ocultar cuentas" : "Ver cuentas"}</button>
        {tanda.estado !== "aplicada" && (
          <SoloLectura>
            <button type="button" disabled={simular.isPending} onClick={() => simular.mutate()} className="rounded border border-line px-2 py-0.5">
              {simular.isPending ? "Calculando…" : "Simular esta tanda"}
            </button>
          </SoloLectura>
        )}
      </div>
      {abierta && (
        <div>
          <p className="mt-1 text-ink-secondary">Los importes son el volumen de cada cuenta en pesos (facturado más pagado; los documentos en dólares, al tipo de cambio de su factura).</p>
          <ul className="mt-1 columns-2 gap-4">
            {tanda.contactos.map((c) => (
              <li key={c.idContacto}>
                <Link className="text-finance underline" href={`/finanzas/auditoria-cuentas/cuenta/${c.idContacto}`}>{c.nombre ?? c.idContacto}</Link>{" "}
                <span className="text-ink-secondary">{formatMoneda(c.volumen)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {error && <p role="alert" className="mt-1 text-status-danger">{error}</p>}
      {r && (
        <div className="mt-2 space-y-1">
          <p>
            Simulación: <b>{r.cierranDespues}</b> de {r.contactos} cuentas cierran, <b>{r.empeoran}</b> empeoran, {r.aplicaciones} imputaciones nuevas.
          </p>
          {omitidas.length > 0 && (
            <details className="text-status-warning">
              <summary className="cursor-pointer">{omitidas.length} cuentas quedaron afuera: todavía no completaron las etapas previas al FIFO</summary>
              <ul className="mt-1 list-disc pl-5">
                {omitidas.map((o) => (
                  <li key={o.idContacto}>
                    <Link className="text-finance underline" href={`/finanzas/auditoria-cuentas/cuenta/${o.idContacto}`}>{tanda.contactos.find((c) => c.idContacto === o.idContacto)?.nombre ?? o.idContacto}</Link>: {o.motivo}
                  </li>
                ))}
              </ul>
            </details>
          )}
          {aplicada ? (
            <p className="text-status-success">
              Tanda aplicada.{" "}
              <button type="button" disabled={deshacer.isPending} onClick={() => deshacer.mutate()} className="ml-2 rounded border border-line px-2 py-0.5">Deshacer</button>
            </p>
          ) : r.empeoran > 0 ? (
            <p className="text-status-danger">Hay cuentas que empeoran: no se aplica esta tanda.</p>
          ) : (
            <SoloLectura>
              <button type="button" disabled={aplicar.isPending} onClick={() => aplicar.mutate()} className="rounded bg-finance px-3 py-1 text-white">
                Aplicar esta tanda (respaldo previo, el saldo no cambia)
              </button>
            </SoloLectura>
          )}
        </div>
      )}
    </li>
  );
}

/** Recálculo de las imputaciones (FIFO) de todos los contactos, en tandas pequeñas de las cuentas más fáciles a las más complicadas. */
export function FifoTandas() {
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["auditoria-fifo-plan"], queryFn: fetchPlanFifo });
  if (isLoading) return <LoadingState />;
  if (isError || !data) return <ErrorState message="No se pudo cargar el plan del FIFO." onRetry={() => refetch()} />;
  if (!data.base) return <p className="text-xs text-ink-secondary">Todavía no hay una simulación de todos los contactos.</p>;
  const r = data.base.resumen;

  return (
    <section className="space-y-2">
      <h2 className="text-sm font-semibold">Imputaciones de todas las cuentas (FIFO)</h2>
      <p className="text-xs text-ink-secondary">
        Simulación del {formatFecha(data.base.fecha)}: de {r.contactos} cuentas, {data.yaCierran} ya cierran y no cambian, {r.mejoran} mejoran y cierran, {r.empeoran} empeoran y {r.excepciones} no cierran (las revisás una por una).
        Cada tanda se simula, se aplica con tu aprobación y se puede deshacer; el saldo de las cuentas no cambia.
      </p>
      <ul className="space-y-1">
        {data.tandas.map((t) => <UnaTanda key={t.numero} tanda={t} />)}
      </ul>
      <details className="text-xs">
        <summary className="cursor-pointer">Cuentas que no cierran con el FIFO ({data.excepciones.length})</summary>
        <ul className="mt-1 columns-2 gap-4">
          {data.excepciones.map((c) => (
            <li key={c.idContacto}>
              <Link className="text-finance underline" href={`/finanzas/auditoria-cuentas/cuenta/${c.idContacto}`}>{c.nombre ?? c.idContacto}</Link>{" "}
              <span className="text-ink-secondary">{formatMoneda(c.volumen)}</span>
            </li>
          ))}
        </ul>
      </details>
    </section>
  );
}
