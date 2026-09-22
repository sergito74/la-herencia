"use client";

import { useState } from "react";

import { formatCantidad } from "@/lib/format";
import { repartirTotal } from "@/lib/repartoInsumo";
import { NumberInput } from "@/components/ui/NumberInput";
import type { GrupoCultivoCampania } from "@/components/ordenes/CultivoCampaniaLotesSelector";
import type { DistribucionIn } from "@/services/ordenesApi";

/**
 * Dosis por hectárea de un renglón de insumo, lote por lote: la dosis puede
 * variar de cultivo a cultivo y de lote a lote. No define la cantidad de cada
 * lote en valor absoluto — es el PESO con el que se reparte la cantidad total
 * que cargó el usuario (dato real del plan del ingeniero agrónomo), en
 * proporción a dosis×superficie de cada lote (hallazgo orden 153: así se
 * calculaban los datos heredados, verificado contra la migración). "Aplicar a
 * todo el grupo" es un atajo para completar rápido cuando la dosis coincide
 * entre lotes de un mismo Cultivo/Campaña.
 */
export function DistribucionLotesPanel({
  grupos,
  cantidadTotal,
  distribuciones,
  onChange,
}: {
  grupos: GrupoCultivoCampania[];
  cantidadTotal: number;
  distribuciones: DistribucionIn[];
  onChange: (distribuciones: DistribucionIn[]) => void;
}) {
  const [dosisAtajo, setDosisAtajo] = useState<Record<string, number | null>>({});

  const clave = (idCultivo: number, idCampania: number) => `${idCultivo}-${idCampania}`;

  const filasDeGrupo = (g: GrupoCultivoCampania) =>
    distribuciones
      .map((d, i) => ({ d, i }))
      .filter(({ d }) => d.idCultivo === g.idCultivo && d.idCampania === g.idCampania);

  const actualizarFila = (i: number, cambios: Partial<DistribucionIn>) => {
    const copia = [...distribuciones];
    copia[i] = { ...copia[i], ...cambios };
    onChange(copia);
  };

  const aplicarAtajoAGrupo = (g: GrupoCultivoCampania) => {
    const k = clave(g.idCultivo, g.idCampania);
    const dosisHa = dosisAtajo[k];
    if (dosisHa == null) return;
    const copia = [...distribuciones];
    for (const { i } of filasDeGrupo(g)) copia[i] = { ...copia[i], dosisHa };
    onChange(copia);
  };

  const gruposConFilas = grupos.map((g) => ({ g, filas: filasDeGrupo(g) })).filter(({ filas }) => filas.length > 0);
  const cantidadPorFila = repartirTotal(cantidadTotal, distribuciones);

  if (gruposConFilas.length === 0) {
    return <p className="text-sm text-ink-secondary">Elegí Cultivo/Campaña y sus lotes arriba antes de cargar la dosis.</p>;
  }

  return (
    <div className="space-y-3 rounded border border-border p-3">
      {gruposConFilas.map(({ g, filas }) => {
        const k = clave(g.idCultivo, g.idCampania);
        const superficieGrupo = filas.filter(({ d }) => d.aplicar).reduce((acc, { d }) => acc + d.superficie, 0);
        const totalGrupo = filas.reduce((acc, { i }) => acc + cantidadPorFila[i], 0);
        return (
          <div key={k} className="rounded border border-border/60 p-2">
            <div className="mb-1 flex flex-wrap items-center gap-3">
              <span className="text-sm font-medium">
                {g.cultivo} — {g.campania}
                <span className="ml-2 font-normal text-ink-secondary">({formatCantidad(superficieGrupo)} ha)</span>
              </span>
              <label className="flex items-center gap-1 text-sm text-ink-secondary">
                Aplicar a todo el grupo
                <NumberInput
                  className="w-20 rounded border border-border px-1 py-0.5 text-right"
                  value={dosisAtajo[k] ?? null}
                  onChange={(v) => setDosisAtajo((actual) => ({ ...actual, [k]: v }))}
                  maxDecimales={4}
                />
              </label>
              <button type="button" onClick={() => aplicarAtajoAGrupo(g)} className="text-sm text-finance hover:underline">
                Completar
              </button>
              <span className="text-sm text-ink-secondary">Le corresponde al grupo: {formatCantidad(totalGrupo)}</span>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-ink-secondary">
                  <th className="pb-1">Lote</th>
                  <th className="pb-1">Superficie</th>
                  <th className="pb-1">Dosis/ha</th>
                  <th className="pb-1">Cantidad (calculada)</th>
                  <th className="pb-1">Aplicar</th>
                </tr>
              </thead>
              <tbody>
                {filas.map(({ d, i }) => {
                  const lote = g.lotes.find((l) => l.idLote === d.idLote);
                  return (
                    <tr key={d.idLote} className="border-t border-border">
                      <td className="py-1 pr-2">{lote?.numeroLote ?? d.idLote}</td>
                      <td className="py-1 pr-2 text-right">{formatCantidad(d.superficie)}</td>
                      <td className="py-1 pr-2">
                        <NumberInput className="w-24 rounded border border-border px-1 py-0.5 text-right" value={d.dosisHa} onChange={(v) => actualizarFila(i, { dosisHa: v ?? 0 })} maxDecimales={4} />
                      </td>
                      <td className="py-1 pr-2 text-right">{formatCantidad(cantidadPorFila[i])}</td>
                      <td className="py-1 pr-2 text-center">
                        <input type="checkbox" checked={d.aplicar} onChange={(e) => actualizarFila(i, { aplicar: e.target.checked })} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        );
      })}
      <div className="flex items-center justify-end">
        <span className="text-sm font-medium">Total del insumo (cargado): {formatCantidad(cantidadTotal)}</span>
      </div>
    </div>
  );
}
