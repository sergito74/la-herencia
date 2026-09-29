"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchContactos, type Contacto } from "@/services/cuentasCorrientesApi";
import {
  origenSoportado,
  reasignarMovimiento,
  type Reasignacion,
} from "@/services/reasignacionContactoApi";
import { ApiError } from "@/services/apiClient";
import { SoloLectura } from "@/components/auth/SoloLectura";
import { filterInputClass } from "@/components/ui/FilterBar";
import { useToast } from "@/components/ui/Toast";

/** Botón "Reasignar" en contexto (022-reasignacion-contacto, US1): permite
 * corregir el contacto de un movimiento puntual de cuenta corriente sin
 * salir de la pantalla. FR-007: si el origen no tiene soporte, se muestra
 * deshabilitado con una explicación en vez de intentar el POST. */
export function ReasignarMovimientoButton({
  origenTipo,
  idOrigen,
  onReasignado,
}: {
  origenTipo: string | null;
  idOrigen: number | null;
  onReasignado: () => void;
}) {
  const { showToast } = useToast();
  const [abierto, setAbierto] = useState(false);
  const [q, setQ] = useState("");
  const [buscado, setBuscado] = useState("");
  const [seleccionado, setSeleccionado] = useState<Contacto | null>(null);
  const [confirmando, setConfirmando] = useState(false);
  const [guardando, setGuardando] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["reasignacion-buscar-contacto", buscado],
    queryFn: () => fetchContactos({ q: buscado }),
    enabled: abierto && buscado.length > 0,
  });

  if (origenTipo === null || idOrigen === null || !origenSoportado(origenTipo)) {
    return (
      <span className="text-xs text-ink-secondary" title="Este tipo de movimiento todavía no admite reasignación.">
        —
      </span>
    );
  }

  async function confirmar() {
    if (!seleccionado) return;
    setGuardando(true);
    try {
      await reasignarMovimiento(origenTipo as string, idOrigen as number, seleccionado.idContacto);
      showToast(`Movimiento reasignado a ${seleccionado.razonSocial ?? seleccionado.idContacto}.`, "success");
      setAbierto(false);
      setConfirmando(false);
      setSeleccionado(null);
      setQ("");
      setBuscado("");
      onReasignado();
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "Error al reasignar el movimiento.", "danger");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <SoloLectura>
      <div className="relative">
        <button
          type="button"
          onClick={() => setAbierto((v) => !v)}
          className="text-xs text-finance underline"
        >
          {abierto ? "Cancelar" : "Reasignar"}
        </button>

        {abierto && (
          <div className="absolute right-0 z-10 mt-1 w-80 space-y-2 rounded-md border border-border bg-surface p-3 text-left shadow-lg">
            {!confirmando && (
              <>
                <input
                  className={filterInputClass}
                  placeholder="Buscar contacto correcto…"
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") setBuscado(q);
                  }}
                />
                {isLoading && <p className="text-xs text-ink-secondary">Buscando…</p>}
                {data && (
                  <ul className="max-h-48 divide-y divide-border overflow-y-auto">
                    {data.items.map((c) => (
                      <li key={c.idContacto}>
                        <button
                          type="button"
                          className="w-full px-1 py-1 text-left text-xs hover:bg-surface-sunken"
                          onClick={() => {
                            setSeleccionado(c);
                            setConfirmando(true);
                          }}
                        >
                          {c.razonSocial ?? "—"}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}

            {confirmando && seleccionado && (
              <div className="space-y-2 text-xs">
                <p>
                  ¿Reasignar este movimiento a <strong>{seleccionado.razonSocial ?? seleccionado.idContacto}</strong>?
                </p>
                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setConfirmando(false);
                      setSeleccionado(null);
                    }}
                    className="rounded border border-border px-2 py-1 hover:bg-surface-sunken"
                  >
                    Volver
                  </button>
                  <button
                    type="button"
                    disabled={guardando}
                    onClick={confirmar}
                    className="rounded bg-finance px-2 py-1 text-white disabled:opacity-50"
                  >
                    {guardando ? "Guardando…" : "Confirmar"}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </SoloLectura>
  );
}

export type { Reasignacion };
