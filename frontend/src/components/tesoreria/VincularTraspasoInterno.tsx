"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  deleteTraspasoInterno,
  fetchEstadoTraspasoInterno,
  postTraspasoInterno,
} from "@/services/traspasosInternosTesoreriaApi";
import { ApiError } from "@/services/apiClient";
import { MEDIO_LABELS } from "@/components/tesoreria/MovimientosPorMedio";
import type { Medio } from "@/services/tesoreriaApi";
import { SoloLectura } from "@/components/auth/SoloLectura";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useToast } from "@/components/ui/Toast";
import { formatFecha, formatMoneda } from "@/lib/format";

const MEDIOS_VINCULABLES: Medio[] = ["bna", "galicia", "mercado-libre", "efectivo", "valores-propios", "valores-recibidos"];

/**
 * Acción de vincular un movimiento de Tesorería con OTRO movimiento (de
 * cualquier medio) que representa el mismo traspaso interno de dinero entre
 * cuentas propias — sin ningún efecto contable (024-traspasos-internos-
 * tesoreria). `estadoExterno` es el `estadoConciliacion` unificado que ya
 * trae la fila del listado (5 valores, calculado por `estado_resolucion` en
 * el backend): si ya es `ya_reconocido`/`conciliado`/`parcialmente_conciliado`,
 * este componente no ofrece vincular (FR-006, mismo criterio que 023 con
 * `ya_reconocido` — la acción contraria no se ofrece cuando el movimiento ya
 * está resuelto por otra vía, remediación US2).
 */
export function VincularTraspasoInterno({
  medio,
  idMovimiento,
  estadoExterno,
}: {
  medio: Medio;
  idMovimiento: number;
  estadoExterno: string | null;
}) {
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const [abierto, setAbierto] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [busquedaMedio, setBusquedaMedio] = useState<Medio>("galicia");
  const [busquedaId, setBusquedaId] = useState("");

  const habilitado = MEDIOS_VINCULABLES.includes(medio);
  const resueltoPorConciliacion =
    estadoExterno === "sin_documento" || estadoExterno === "ya_reconocido" || estadoExterno === "conciliado" || estadoExterno === "parcialmente_conciliado";

  const estadoQuery = useQuery({
    queryKey: ["traspaso-interno-estado", medio, idMovimiento],
    queryFn: () => fetchEstadoTraspasoInterno(medio, idMovimiento),
    enabled: habilitado && (abierto || estadoExterno === "traspaso_interno"),
  });

  if (!habilitado) return <span className="text-xs text-ink-secondary">—</span>;
  if (resueltoPorConciliacion) return <span className="text-xs text-ink-secondary">—</span>;

  function refrescar() {
    queryClient.invalidateQueries({ queryKey: ["traspaso-interno-estado", medio, idMovimiento] });
    queryClient.invalidateQueries({ queryKey: ["tesoreria-movimientos"] });
  }

  async function vincularCon(medioB: Medio, idMovimientoB: number) {
    setGuardando(true);
    try {
      await postTraspasoInterno(medio, idMovimiento, { medioB, idMovimientoB });
      showToast("Traspaso interno vinculado.", "success");
      setAbierto(false);
      refrescar();
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "Error al vincular el traspaso interno.", "danger");
    } finally {
      setGuardando(false);
    }
  }

  async function deshacer() {
    setGuardando(true);
    try {
      await deleteTraspasoInterno(medio, idMovimiento);
      showToast("Vínculo de traspaso interno deshecho.", "success");
      refrescar();
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "Error al deshacer el vínculo.", "danger");
    } finally {
      setGuardando(false);
    }
  }

  if (estadoExterno === "traspaso_interno") {
    const contraparte = estadoQuery.data?.contraparte;
    return (
      <SoloLectura>
        <div className="flex items-center gap-2">
          <StatusBadge label="Traspaso interno" tone="success" />
          {contraparte && (
            <span className="text-xs text-ink-secondary">
              {MEDIO_LABELS[contraparte.medio]} #{contraparte.idMovimiento} — {formatMoneda(contraparte.importe)}
            </span>
          )}
          <button type="button" disabled={guardando} onClick={deshacer} className="text-xs text-finance underline disabled:opacity-50">
            {guardando ? "Deshaciendo…" : "Deshacer"}
          </button>
        </div>
      </SoloLectura>
    );
  }

  return (
    <SoloLectura>
      <div className="relative">
        <button type="button" onClick={() => setAbierto((v) => !v)} className="text-xs text-finance underline">
          {abierto ? "Cancelar" : "Traspaso interno…"}
        </button>

        {abierto && (
          <div className="absolute right-0 z-10 mt-1 w-96 space-y-2 rounded-md border border-border bg-surface p-3 text-left text-xs shadow-lg">
            {estadoQuery.data && estadoQuery.data.candidatas.length > 0 && (
              <div className="space-y-1">
                <p className="font-medium text-ink-primary">Candidatas sugeridas:</p>
                {estadoQuery.data.candidatas.map((c) => (
                  <button
                    key={`${c.medio}-${c.idMovimiento}`}
                    type="button"
                    disabled={guardando}
                    onClick={() => vincularCon(c.medio, c.idMovimiento)}
                    className="block w-full rounded border border-border px-2 py-1 text-left hover:bg-surface-sunken disabled:opacity-50"
                  >
                    {MEDIO_LABELS[c.medio]} #{c.idMovimiento} — {formatFecha(c.fecha)} — {formatMoneda(c.importe)}
                    {c.descripcion ? ` — ${c.descripcion}` : ""}
                  </button>
                ))}
              </div>
            )}

            <div className="space-y-1 border-t border-border pt-2">
              <p className="font-medium text-ink-primary">Buscar manualmente:</p>
              <div className="flex gap-1">
                <select
                  className="rounded border border-border px-1 py-1"
                  value={busquedaMedio}
                  onChange={(e) => setBusquedaMedio(e.target.value as Medio)}
                >
                  {MEDIOS_VINCULABLES.filter((m) => m !== medio).map((m) => (
                    <option key={m} value={m}>
                      {MEDIO_LABELS[m]}
                    </option>
                  ))}
                </select>
                <input
                  className="w-24 rounded border border-border px-1.5 py-1"
                  placeholder="Id movimiento"
                  value={busquedaId}
                  onChange={(e) => setBusquedaId(e.target.value)}
                />
                <button
                  type="button"
                  disabled={guardando || !busquedaId.trim()}
                  onClick={() => vincularCon(busquedaMedio, Number(busquedaId))}
                  className="rounded bg-finance px-2 py-1 text-white disabled:opacity-50"
                >
                  Vincular
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </SoloLectura>
  );
}
