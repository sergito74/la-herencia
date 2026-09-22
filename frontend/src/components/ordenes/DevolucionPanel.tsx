"use client";

import { useState } from "react";

import { ApiError } from "@/services/apiClient";
import { formatCantidad } from "@/lib/format";
import { NumberInput } from "@/components/ui/NumberInput";
import { registrarDevolucion, type RenglonInsumoDetalle } from "@/services/ordenesApi";
import { useToast } from "@/components/ui/Toast";

/** Devolución de insumo no utilizado (Historia 2): reingresa al stock y ajusta
 * el cierre del renglón (FR-004/FR-009). */
export function DevolucionPanel({ idOrden, renglon, onGuardada }: { idOrden: number; renglon: RenglonInsumoDetalle; onGuardada: () => void }) {
  const { showToast } = useToast();
  const [abierto, setAbierto] = useState(false);
  const [cantidad, setCantidad] = useState<number | null>(null);
  const [fecha, setFecha] = useState(new Date().toISOString().slice(0, 10));
  const [guardando, setGuardando] = useState(false);

  const devuelto = renglon.devoluciones.reduce((acc, d) => acc + d.cantidad, 0);
  const disponible = renglon.cantidadTotal - devuelto;

  async function confirmar() {
    if (!cantidad || cantidad <= 0) return;
    setGuardando(true);
    try {
      await registrarDevolucion(idOrden, renglon.idOrdenInsumo, { fecha, cantidad });
      showToast("Devolución registrada, el stock se actualizó.", "success");
      setAbierto(false);
      setCantidad(null);
      onGuardada();
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "No se pudo registrar la devolución.", "danger");
    } finally {
      setGuardando(false);
    }
  }

  if (disponible <= 0) return null;

  return (
    <div className="mt-1 text-sm">
      {!abierto ? (
        <button type="button" onClick={() => setAbierto(true)} className="text-finance underline">
          Registrar devolución (disponible: {formatCantidad(disponible)})
        </button>
      ) : (
        <div className="flex items-center gap-2 rounded border border-border p-2">
          <input type="date" className="rounded border border-border px-2 py-1" value={fecha} onChange={(e) => setFecha(e.target.value)} />
          <NumberInput className="w-24 rounded border border-border px-2 py-1 text-right" value={cantidad} onChange={setCantidad} maxDecimales={4} placeholder="Cantidad" />
          <button type="button" onClick={confirmar} disabled={guardando || !cantidad} className="rounded bg-finance px-2 py-1 text-white disabled:opacity-50">
            Confirmar
          </button>
          <button type="button" onClick={() => setAbierto(false)} className="rounded border border-border px-2 py-1">
            Cancelar
          </button>
        </div>
      )}
    </div>
  );
}
