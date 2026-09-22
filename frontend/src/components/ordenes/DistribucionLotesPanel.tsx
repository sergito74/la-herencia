"use client";

import { formatCantidad } from "@/lib/format";
import { NumberInput } from "@/components/ui/NumberInput";
import type { Campania, Cultivo, DistribucionIn, Lote } from "@/services/ordenesApi";

/**
 * Reparto de un renglón de insumo entre lotes: el ingeniero agronómico elige el
 * lote y carga la dosis por hectárea; la cantidad se calcula (dosisHa ×
 * superficie) y se suma para dar el total del insumo a retirar (FR-003).
 */
export function DistribucionLotesPanel({
  lotes,
  cultivos,
  campanias,
  distribuciones,
  onChange,
}: {
  lotes: Lote[];
  cultivos: Cultivo[];
  campanias: Campania[];
  distribuciones: DistribucionIn[];
  onChange: (distribuciones: DistribucionIn[]) => void;
}) {
  const agregarLote = () => {
    const primerLote = lotes[0];
    if (!primerLote) return;
    onChange([
      ...distribuciones,
      {
        idLote: primerLote.idLote,
        idCultivo: cultivos[0]?.idCultivo ?? 0,
        idCampania: campanias[0]?.idCampania ?? 0,
        dosisHa: 0,
        superficie: primerLote.superficie,
        aplicar: true,
      },
    ]);
  };

  const actualizar = (i: number, cambios: Partial<DistribucionIn>) => {
    const copia = [...distribuciones];
    copia[i] = { ...copia[i], ...cambios };
    onChange(copia);
  };

  const quitar = (i: number) => onChange(distribuciones.filter((_, idx) => idx !== i));

  const total = distribuciones.filter((d) => d.aplicar).reduce((acc, d) => acc + d.dosisHa * d.superficie, 0);

  return (
    <div className="rounded border border-border p-3">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-ink-secondary">
            <th className="pb-1">Lote</th>
            <th className="pb-1">Cultivo</th>
            <th className="pb-1">Campaña</th>
            <th className="pb-1">Dosis/ha</th>
            <th className="pb-1">Superficie</th>
            <th className="pb-1">Cantidad</th>
            <th className="pb-1">Aplicar</th>
            <th className="pb-1" />
          </tr>
        </thead>
        <tbody>
          {distribuciones.map((d, i) => (
            <tr key={i} className="border-t border-border">
              <td className="py-1 pr-2">
                <select
                  className="w-24 rounded border border-border px-1 py-0.5"
                  value={d.idLote}
                  onChange={(e) => {
                    const lote = lotes.find((l) => l.idLote === Number(e.target.value));
                    actualizar(i, { idLote: Number(e.target.value), superficie: lote?.superficie ?? d.superficie });
                  }}
                >
                  {lotes.map((l) => (
                    <option key={l.idLote} value={l.idLote}>
                      {l.numeroLote}
                    </option>
                  ))}
                </select>
              </td>
              <td className="py-1 pr-2">
                <select className="w-32 rounded border border-border px-1 py-0.5" value={d.idCultivo} onChange={(e) => actualizar(i, { idCultivo: Number(e.target.value) })}>
                  {cultivos.map((c) => (
                    <option key={c.idCultivo} value={c.idCultivo}>
                      {c.nombre}
                    </option>
                  ))}
                </select>
              </td>
              <td className="py-1 pr-2">
                <select className="w-28 rounded border border-border px-1 py-0.5" value={d.idCampania} onChange={(e) => actualizar(i, { idCampania: Number(e.target.value) })}>
                  {campanias.map((c) => (
                    <option key={c.idCampania} value={c.idCampania}>
                      {c.nombre}
                    </option>
                  ))}
                </select>
              </td>
              <td className="py-1 pr-2">
                <NumberInput className="w-20 rounded border border-border px-1 py-0.5 text-right" value={d.dosisHa} onChange={(v) => actualizar(i, { dosisHa: v ?? 0 })} maxDecimales={4} />
              </td>
              <td className="py-1 pr-2">
                <NumberInput className="w-20 rounded border border-border px-1 py-0.5 text-right" value={d.superficie} onChange={(v) => actualizar(i, { superficie: v ?? 0 })} maxDecimales={2} />
              </td>
              <td className="py-1 pr-2 text-right">{formatCantidad(d.dosisHa * d.superficie)}</td>
              <td className="py-1 pr-2 text-center">
                <input type="checkbox" checked={d.aplicar} onChange={(e) => actualizar(i, { aplicar: e.target.checked })} />
              </td>
              <td className="py-1">
                <button type="button" onClick={() => quitar(i)} className="text-status-danger hover:underline">
                  Quitar
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-2 flex items-center justify-between">
        <button type="button" onClick={agregarLote} className="rounded border border-border px-2 py-1 text-sm hover:bg-surface-sunken">
          + Agregar lote
        </button>
        <span className="text-sm font-medium">Total del insumo: {formatCantidad(total)}</span>
      </div>
    </div>
  );
}
