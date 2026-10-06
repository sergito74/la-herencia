"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatFecha, formatMoneda } from "@/lib/format";
import {
  aprobarCruce,
  deshacerCruce,
  fetchCruces,
  fetchSugerenciasCruce,
  type SugerenciaCruce,
  type TipoCruce,
} from "@/services/tarjetasCuentaApi";

const TITULOS: Record<TipoCruce, string> = {
  "devolucion-debito": "Devoluciones del banco para cruzar con su débito",
  "consumo-devolucion": "Devoluciones de Mercado Pago para cruzar con un consumo",
};

function Descripcion({ m }: { m: { fecha: string | null; importe: number; concepto: string | null } }) {
  return (
    <span>
      {formatFecha(m.fecha)} · {formatMoneda(m.importe)} · {m.concepto ?? "—"}
    </span>
  );
}

function Sugerencias({ tipo }: { tipo: TipoCruce }) {
  const qc = useQueryClient();
  const [confirmar, setConfirmar] = useState<SugerenciaCruce | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["tarjetas-cruces-sugerencias", tipo],
    queryFn: () => fetchSugerenciasCruce({ tipo }),
  });
  const aprobar = useMutation({
    mutationFn: (s: SugerenciaCruce) =>
      aprobarCruce({
        tipo: s.tipo,
        idTarjeta: s.idTarjeta,
        sugerido: true,
        origen: { medio: s.origen.medio, idMovimiento: s.origen.idMovimiento },
        destino: s.destino && tipo === "devolucion-debito" ? { medio: s.destino.medio, idMovimiento: s.destino.idMovimiento } : undefined,
        idLineaConsumo: tipo === "consumo-devolucion" ? s.destino?.idMovimiento : undefined,
      }),
    onSuccess: () => {
      setConfirmar(null);
      setError(null);
      qc.invalidateQueries({ queryKey: ["tarjetas-cruces-sugerencias"] });
      qc.invalidateQueries({ queryKey: ["tarjetas-cruces"] });
      qc.invalidateQueries({ queryKey: ["tarjetas-cuenta-control"] });
      qc.invalidateQueries({ queryKey: ["tarjetas-cuenta-resumen"] });
      qc.invalidateQueries({ queryKey: ["tarjeta-cuenta"] });
    },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : "No se pudo registrar el cruce."),
  });

  if (isLoading) return <LoadingState />;
  if (isError || !data) return <ErrorState message="No se pudieron cargar las sugerencias." onRetry={() => refetch()} />;

  return (
    <section className="space-y-2">
      <h3 className="text-sm font-semibold">{TITULOS[tipo]}</h3>
      {data.sugerencias.length === 0 && <p className="text-xs text-ink-secondary">No hay sugerencias pendientes.</p>}
      {data.sugerencias.map((s, i) => (
        <div key={i} className="rounded border border-line p-3 text-sm">
          <p><b>Devolución:</b> <Descripcion m={s.origen} /></p>
          {s.destino && (
            <p><b>{tipo === "devolucion-debito" ? "Débito" : "Consumo"}:</b> <Descripcion m={s.destino} /></p>
          )}
          <p className="text-xs text-ink-secondary">
            {s.diasDiferencia} días de diferencia · diferencia de importe {formatMoneda(s.diferenciaImporte)}
          </p>
          <SoloLectura>
            <div className="mt-2 flex gap-2">
              <button type="button" onClick={() => setConfirmar(s)} className="rounded bg-finance px-3 py-1 text-xs text-white">
                Revisar y aprobar
              </button>
            </div>
          </SoloLectura>
        </div>
      ))}

      {confirmar && (
        <div role="dialog" aria-modal className="rounded border border-finance bg-surface p-4 text-sm shadow">
          <p className="font-medium">¿Confirmás este cruce?</p>
          <p className="mt-1 text-xs">
            La devolución de {formatMoneda(confirmar.origen.importe)} se registra como devolución de lo que se pagó a la tarjeta
            {tipo === "devolucion-debito" ? ": el saldo de la tarjeta queda corregido." : ": el consumo queda cancelado."} Podés deshacerlo después.
          </p>
          {error && <p role="alert" className="mt-1 text-xs text-status-danger">{error}</p>}
          <div className="mt-2 flex gap-2">
            <button type="button" disabled={aprobar.isPending} onClick={() => aprobar.mutate(confirmar)}
              className="rounded bg-finance px-3 py-1 text-xs text-white">
              Aprobar cruce
            </button>
            <button type="button" onClick={() => { setConfirmar(null); setError(null); }}
              className="rounded border border-line px-3 py-1 text-xs">
              Cancelar
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

function Historial() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["tarjetas-cruces"], queryFn: () => fetchCruces(true) });
  const deshacer = useMutation({
    mutationFn: (id: number) => deshacerCruce(id),
    onSuccess: () => {
      for (const k of ["tarjetas-cruces", "tarjetas-cruces-sugerencias", "tarjetas-cuenta-control", "tarjetas-cuenta-resumen", "tarjeta-cuenta"])
        qc.invalidateQueries({ queryKey: [k] });
    },
  });
  if (isLoading) return <LoadingState />;
  return (
    <section className="space-y-1">
      <h3 className="text-sm font-semibold">Cruces registrados</h3>
      {(data ?? []).length === 0 && <p className="text-xs text-ink-secondary">Todavía no hay cruces.</p>}
      <ul className="text-xs">
        {(data ?? []).map((c) => (
          <li key={c.idCruce} className={`flex items-center gap-2 border-t border-line py-1 ${c.deshecho ? "text-ink-secondary line-through" : ""}`}>
            <span>
              #{c.idCruce} · {c.tipo === "devolucion-debito" ? "Devolución de débito" : "Devolución de consumo"} · {formatMoneda(c.importe)} ·{" "}
              {c.usuario} {formatFecha(c.fecha)}
              {c.deshecho ? ` · deshecho por ${c.usuarioDeshecho}` : ""}
            </span>
            {!c.deshecho && (
              <SoloLectura>
                <button type="button" onClick={() => deshacer.mutate(c.idCruce)} className="rounded border border-line px-2 py-0.5 no-underline">
                  Deshacer
                </button>
              </SoloLectura>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Sugerencias de cruce, aprobación con visto bueno e historial (034, US4/US5). */
export function PanelCruces() {
  return (
    <div className="space-y-4">
      <Sugerencias tipo="devolucion-debito" />
      <Sugerencias tipo="consumo-devolucion" />
      <Historial />
    </div>
  );
}
