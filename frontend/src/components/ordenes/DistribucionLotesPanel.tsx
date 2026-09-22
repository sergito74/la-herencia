"use client";

import { formatCantidad } from "@/lib/format";
import { NumberInput } from "@/components/ui/NumberInput";
import type { DistribucionIn } from "@/services/ordenesApi";

/**
 * Dosis por hectárea de un renglón de insumo, sobre el set de lotes que ya
 * eligió la orden (`CultivoCampaniaLotesSelector`, a nivel de orden, no por
 * renglón). Cada fila corresponde a un lote incluido; la cantidad se calcula
 * (dosisHa × superficie) y se suma para dar el total del insumo (FR-003).
 */
export function DistribucionLotesPanel({
  distribuciones,
  lotePorId,
  cultivoPorId,
  campaniaPorId,
  onChange,
}: {
  distribuciones: DistribucionIn[];
  lotePorId: Record<number, string>;
  cultivoPorId: Record<number, string>;
  campaniaPorId: Record<number, string>;
  onChange: (distribuciones: DistribucionIn[]) => void;
}) {
  const actualizar = (i: number, cambios: Partial<DistribucionIn>) => {
    const copia = [...distribuciones];
    copia[i] = { ...copia[i], ...cambios };
    onChange(copia);
  };

  const total = distribuciones.filter((d) => d.aplicar).reduce((acc, d) => acc + d.dosisHa * d.superficie, 0);

  if (distribuciones.length === 0) {
    return <p className="text-sm text-ink-secondary">Elegí Cultivo/Campaña y sus lotes arriba antes de cargar la dosis.</p>;
  }

  return (
    <div className="rounded border border-border p-3">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-ink-secondary">
            <th className="pb-1">Lote</th>
            <th className="pb-1">Cultivo</th>
            <th className="pb-1">Campaña</th>
            <th className="pb-1">Superficie</th>
            <th className="pb-1">Dosis/ha</th>
            <th className="pb-1">Cantidad</th>
            <th className="pb-1">Aplicar</th>
          </tr>
        </thead>
        <tbody>
          {distribuciones.map((d, i) => (
            <tr key={`${d.idLote}-${d.idCultivo}-${d.idCampania}`} className="border-t border-border">
              <td className="py-1 pr-2">{lotePorId[d.idLote] ?? d.idLote}</td>
              <td className="py-1 pr-2">{cultivoPorId[d.idCultivo] ?? d.idCultivo}</td>
              <td className="py-1 pr-2">{campaniaPorId[d.idCampania] ?? d.idCampania}</td>
              <td className="py-1 pr-2 text-right">{formatCantidad(d.superficie)}</td>
              <td className="py-1 pr-2">
                <NumberInput className="w-24 rounded border border-border px-1 py-0.5 text-right" value={d.dosisHa} onChange={(v) => actualizar(i, { dosisHa: v ?? 0 })} maxDecimales={4} />
              </td>
              <td className="py-1 pr-2 text-right">{formatCantidad(d.dosisHa * d.superficie)}</td>
              <td className="py-1 pr-2 text-center">
                <input type="checkbox" checked={d.aplicar} onChange={(e) => actualizar(i, { aplicar: e.target.checked })} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-2 flex items-center justify-end">
        <span className="text-sm font-medium">Total del insumo: {formatCantidad(total)}</span>
      </div>
    </div>
  );
}
