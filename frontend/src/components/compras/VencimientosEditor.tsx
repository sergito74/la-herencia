"use client";

import { useEffect, useState } from "react";

import { filterInputClass } from "@/components/ui/FilterBar";
import { MoneyInput } from "@/components/ui/MoneyInput";
import { formatMoneda } from "@/lib/format";
import type { MonedaCompra, VencimientoInput } from "@/services/comprasApi";

const centavos = (n: number) => Math.round(n * 100) / 100;

/** Reparte el total en partes iguales; el último vencimiento absorbe el redondeo para que la suma cierre exacta. */
export function repartirTotal(total: number, cantidad: number): number[] {
  if (cantidad <= 0) return [];
  const parte = centavos(total / cantidad);
  const partes = Array.from({ length: cantidad }, () => parte);
  partes[cantidad - 1] = centavos(total - parte * (cantidad - 1));
  return partes;
}

/**
 * Fechas de vencimiento de pago con el importe de cada una (12/11/2026, pedido de Sergio), visible solo cuando la
 * condición de pago es "A Plazo". Por defecto el total se divide en partes iguales entre las fechas y se recalcula al
 * agregar o quitar fechas o al cambiar el total; si se edita un importe a mano, deja de repartirse solo.
 */
export function VencimientosEditor({
  vencimientos,
  onChange,
  total,
  moneda,
}: {
  vencimientos: VencimientoInput[];
  onChange: (vencimientos: VencimientoInput[]) => void;
  total: number;
  moneda: MonedaCompra;
}) {
  // Manual si la compra ya traía importes guardados; si no, reparto automático.
  const [manual, setManual] = useState(() => vencimientos.some((v) => v.importe != null));

  const repartidos = (lista: VencimientoInput[]) => {
    const partes = repartirTotal(total, lista.length);
    return lista.map((v, i) => ({ ...v, importe: partes[i] }));
  };

  useEffect(() => {
    if (manual || vencimientos.length === 0) return;
    const nuevos = repartidos(vencimientos);
    if (nuevos.some((v, i) => v.importe !== vencimientos[i].importe)) onChange(nuevos);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [total, vencimientos.length, manual]);

  const cambiar = (lista: VencimientoInput[]) => onChange(manual ? lista : repartidos(lista));
  const suma = centavos(vencimientos.reduce((a, v) => a + (v.importe ?? 0), 0));
  const diferencia = centavos(total - suma);

  return (
    <div className="flex flex-wrap items-center gap-2">
      {vencimientos.map((v, i) => (
        <div key={i} className="flex items-center gap-1 rounded-sm border border-border bg-surface px-1 py-0.5">
          <input
            type="date"
            required
            aria-label={`Fecha del vencimiento ${i + 1}`}
            className={filterInputClass}
            value={v.fechaVencimiento}
            onChange={(e) => cambiar(vencimientos.map((x, j) => (j === i ? { ...x, fechaVencimiento: e.target.value } : x)))}
          />
          <MoneyInput
            aria-label={`Importe del vencimiento ${i + 1}`}
            className="w-32 rounded-sm border border-border bg-surface px-2 py-1 text-right text-sm"
            moneda={moneda}
            value={v.importe ?? 0}
            onChange={(valor) => {
              setManual(true);
              onChange(vencimientos.map((x, j) => (j === i ? { ...x, importe: valor } : x)));
            }}
          />
          <button
            type="button"
            aria-label={`Quitar vencimiento ${i + 1}`}
            onClick={() => cambiar(vencimientos.filter((_, j) => j !== i))}
            className="rounded-sm px-1.5 py-0.5 text-xs text-ink-secondary hover:text-status-danger"
          >
            ✕
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={() => cambiar([...vencimientos, { fechaVencimiento: "", importe: 0 }])}
        className="rounded-sm border border-border px-2 py-1 text-xs text-ink-secondary hover:border-border-strong hover:text-ink-primary"
      >
        + Agregar fecha
      </button>
      {vencimientos.length > 1 && manual && (
        <button type="button" onClick={() => { setManual(false); onChange(repartidos(vencimientos)); }}
          className="text-xs text-finance hover:underline" title="Dividir el total en partes iguales">
          Repartir en partes iguales
        </button>
      )}
      {vencimientos.length > 0 && Math.abs(diferencia) > 0.005 && (
        <span role="alert" className="text-xs text-status-danger">
          Falta asignar {formatMoneda(diferencia, moneda)} (suma {formatMoneda(suma, moneda)})
        </span>
      )}
    </div>
  );
}
