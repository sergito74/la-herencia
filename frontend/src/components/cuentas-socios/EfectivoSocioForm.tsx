"use client";

import { useState } from "react";

import { OperacionCajaForm } from "@/components/cajas-efectivo/OperacionCajaForm";
import type { CajaSlug, TipoOperacionCaja } from "@/services/cajasEfectivoApi";

/** Aporte o retiro en efectivo de un socio: es una operación de caja (038) que mueve la caja y la cuenta del socio juntas. */
export function EfectivoSocioForm({ idSocio, onListo }: { idSocio: number; onListo: () => void }) {
  const [caja, setCaja] = useState<CajaSlug>("giamigli-sa");
  const [tipo, setTipo] = useState<TipoOperacionCaja>("aporte");
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 text-sm">
        <label>Caja
          <select className="mt-1 block w-full rounded-sm border border-border bg-surface px-3 py-2" value={caja} onChange={(e) => setCaja(e.target.value as CajaSlug)}>
            <option value="giamigli-sa">Giamigli SA</option>
            <option value="giamigli-dolares">Giamigli US$ (billetes)</option>
            <option value="campo-chica">Caja chica del campo</option>
          </select>
        </label>
        <label>Qué hace el socio
          <select className="mt-1 block w-full rounded-sm border border-border bg-surface px-3 py-2" value={tipo} onChange={(e) => setTipo(e.target.value as TipoOperacionCaja)}>
            <option value="aporte">Aporta efectivo a la caja</option>
            <option value="retiro_a_cuenta">Retira a cuenta (queda debiendo)</option>
            <option value="retiro_ganancias">Retiro de ganancias (no genera deuda)</option>
          </select>
        </label>
      </div>
      <OperacionCajaForm key={`${caja}-${tipo}`} caja={caja} initial={{ tipo, idSocio }} onSaved={onListo} />
    </div>
  );
}
