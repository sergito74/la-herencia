"use client";

import { useState } from "react";

import { formatCantidad } from "@/lib/format";
import { NumberInput } from "@/components/ui/NumberInput";
import type { GrupoCultivoCampania } from "@/components/ordenes/CultivoCampaniaLotesSelector";
import type { DistribucionIn } from "@/services/ordenesApi";

/**
 * Dosis por hectárea de un renglón de insumo: se carga UNA vez por
 * Cultivo/Campaña (así es como lo manda el ingeniero agronómico — la misma
 * dosis para todos los lotes de un mismo momento de aplicación) y se reparte
 * automáticamente entre sus lotes según la superficie de cada uno (FR-003).
 * Si un lote puntual necesita una dosis distinta, "Personalizar por lote"
 * habilita editarlo sin tocar el resto del grupo.
 */
export function DistribucionLotesPanel({
  grupos,
  distribuciones,
  onChange,
}: {
  grupos: GrupoCultivoCampania[];
  distribuciones: DistribucionIn[];
  onChange: (distribuciones: DistribucionIn[]) => void;
}) {
  const [personalizados, setPersonalizados] = useState<Set<string>>(new Set());

  const clave = (idCultivo: number, idCampania: number) => `${idCultivo}-${idCampania}`;

  const filasDeGrupo = (g: GrupoCultivoCampania) =>
    distribuciones
      .map((d, i) => ({ d, i }))
      .filter(({ d }) => d.idCultivo === g.idCultivo && d.idCampania === g.idCampania);

  const dosisUniformeDeGrupo = (filas: { d: DistribucionIn }[]) => {
    if (filas.length === 0) return 0;
    const primera = filas[0].d.dosisHa;
    return filas.every((f) => f.d.dosisHa === primera) ? primera : null;
  };

  const aplicarDosisAGrupo = (g: GrupoCultivoCampania, dosisHa: number) => {
    const copia = [...distribuciones];
    for (const { i } of filasDeGrupo(g)) copia[i] = { ...copia[i], dosisHa };
    onChange(copia);
  };

  const actualizarFila = (i: number, cambios: Partial<DistribucionIn>) => {
    const copia = [...distribuciones];
    copia[i] = { ...copia[i], ...cambios };
    onChange(copia);
  };

  const alternarPersonalizar = (g: GrupoCultivoCampania) => {
    const k = clave(g.idCultivo, g.idCampania);
    setPersonalizados((actual) => {
      const copia = new Set(actual);
      if (copia.has(k)) copia.delete(k);
      else copia.add(k);
      return copia;
    });
  };

  const gruposConFilas = grupos.map((g) => ({ g, filas: filasDeGrupo(g) })).filter(({ filas }) => filas.length > 0);
  const total = distribuciones.filter((d) => d.aplicar).reduce((acc, d) => acc + d.dosisHa * d.superficie, 0);

  if (gruposConFilas.length === 0) {
    return <p className="text-sm text-ink-secondary">Elegí Cultivo/Campaña y sus lotes arriba antes de cargar la dosis.</p>;
  }

  return (
    <div className="space-y-3 rounded border border-border p-3">
      {gruposConFilas.map(({ g, filas }) => {
        const k = clave(g.idCultivo, g.idCampania);
        const dosisUniforme = dosisUniformeDeGrupo(filas);
        const abierto = personalizados.has(k) || dosisUniforme === null;
        const superficieGrupo = filas.filter(({ d }) => d.aplicar).reduce((acc, { d }) => acc + d.superficie, 0);
        const totalGrupo = filas.filter(({ d }) => d.aplicar).reduce((acc, { d }) => acc + d.dosisHa * d.superficie, 0);
        return (
          <div key={k} className="rounded border border-border/60 p-2">
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-sm font-medium">
                {g.cultivo} — {g.campania}
                <span className="ml-2 font-normal text-ink-secondary">({formatCantidad(superficieGrupo)} ha)</span>
              </span>
              <label className="flex items-center gap-1 text-sm">
                Dosis/ha
                <NumberInput
                  className="w-24 rounded border border-border px-1 py-0.5 text-right"
                  value={dosisUniforme}
                  onChange={(v) => aplicarDosisAGrupo(g, v ?? 0)}
                  maxDecimales={4}
                />
              </label>
              <span className="text-sm text-ink-secondary">Total del grupo: {formatCantidad(totalGrupo)}</span>
              <button type="button" onClick={() => alternarPersonalizar(g)} className="text-sm text-finance hover:underline">
                {abierto ? "Ocultar detalle por lote" : "Personalizar por lote"}
              </button>
            </div>
            {abierto && (
              <table className="mt-2 w-full text-sm">
                <thead>
                  <tr className="text-left text-ink-secondary">
                    <th className="pb-1">Lote</th>
                    <th className="pb-1">Superficie</th>
                    <th className="pb-1">Dosis/ha</th>
                    <th className="pb-1">Cantidad</th>
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
                        <td className="py-1 pr-2 text-right">{formatCantidad(d.dosisHa * d.superficie)}</td>
                        <td className="py-1 pr-2 text-center">
                          <input type="checkbox" checked={d.aplicar} onChange={(e) => actualizarFila(i, { aplicar: e.target.checked })} />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        );
      })}
      <div className="flex items-center justify-end">
        <span className="text-sm font-medium">Total del insumo: {formatCantidad(total)}</span>
      </div>
    </div>
  );
}
