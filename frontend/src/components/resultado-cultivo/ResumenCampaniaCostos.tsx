"use client";
import { useQuery } from "@tanstack/react-query";

import { Segmentos } from "@/components/ui/Segmentos";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatCantidad, formatMoneda } from "@/lib/format";
import { fetchCampanias, fetchResultadoCampania } from "@/services/resultadoCultivoApi";

/** Arranque de "Costo por cultivo" (auditoría de diseño 18/11/2026): la campaña vigente con todos sus cultivos, en vez de una
 * pantalla en blanco. Clic en un cultivo abre el formulario de costos (el de Access, sin cambios). */
export function ResumenCampaniaCostos({ idCampania, onCampania, onCultivo }: {
  idCampania: number | null; onCampania: (id: number) => void; onCultivo: (idCultivo: number, idCampania: number) => void;
}) {
  const cat = useQuery({ queryKey: ["rc-campanias"], queryFn: fetchCampanias });
  const actual = idCampania ?? cat.data?.campaniaActualId ?? null;
  const res = useQuery({ queryKey: ["rc-campania", actual], queryFn: () => fetchResultadoCampania(actual as number), enabled: actual != null });
  const recientes = (cat.data?.campanias ?? []).filter((c) => /^\d{4}\/\d{4}$/.test(c.campania)).sort((a, b) => b.campania.localeCompare(a.campania)).slice(0, 4);
  const porHa = (v: number, ha: number) => (ha > 0 ? v / ha : null);

  return (
    <section className="space-y-3">
      {recientes.length > 0 && actual != null && (
        <Segmentos<string> etiqueta="Campaña" valor={String(actual)} onChange={(v) => onCampania(Number(v))}
          opciones={recientes.map((c) => ({ id: String(c.idCampania), label: c.campania }))} />
      )}
      {res.isLoading ? <LoadingState rows={5} /> : res.isError ? <ErrorState message="No se pudo calcular la campaña." onRetry={() => res.refetch()} /> : res.data && (
        <div className="overflow-auto max-h-[calc(100vh-7rem)] rounded-lg border border-border bg-surface">
          <table className="w-full text-sm">
            <thead className="sticky top-0 z-10 bg-surface-sunken text-xs text-ink-secondary">
              <tr>
                <th className="px-3 py-2 text-left">Cultivo</th><th className="px-3 py-2 text-right">Ha sembradas</th>
                <th className="px-3 py-2 text-right">Costo $</th><th className="px-3 py-2 text-right">Costo us$</th>
                <th className="px-3 py-2 text-right">$ / ha</th><th className="px-3 py-2 text-right">us$ / ha</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {res.data.cultivos.map((c) => (
                <tr key={c.idCultivo} className="cursor-pointer hover:bg-surface-sunken/60" title="Ver el detalle de costos" onClick={() => onCultivo(c.idCultivo, res.data!.idCampania)}>
                  <td className="px-3 py-1.5 font-medium">{c.cultivo}</td>
                  <td className="px-3 py-1.5 text-right font-data">{formatCantidad(c.superficieSembrada)}</td>
                  <td className="px-3 py-1.5 text-right font-data">{formatMoneda(c.costoTotalPesos)}</td>
                  <td className="px-3 py-1.5 text-right font-data">{formatMoneda(c.costoTotalDolares, "Dolares")}</td>
                  <td className="px-3 py-1.5 text-right font-data text-ink-secondary">{porHa(c.costoTotalPesos, c.superficieSembrada) != null ? formatMoneda(porHa(c.costoTotalPesos, c.superficieSembrada)!) : "—"}</td>
                  <td className="px-3 py-1.5 text-right font-data text-ink-secondary">{porHa(c.costoTotalDolares, c.superficieSembrada) != null ? formatMoneda(porHa(c.costoTotalDolares, c.superficieSembrada)!, "Dolares") : "—"}</td>
                </tr>
              ))}
            </tbody>
            <tfoot className="border-t border-border font-medium">
              <tr>
                <td className="px-3 py-2">Total campaña {res.data.campania}</td>
                <td className="px-3 py-2 text-right font-data">{formatCantidad(res.data.superficieSembrada)}</td>
                <td className="px-3 py-2 text-right font-data">{formatMoneda(res.data.costoTotalPesos)}</td>
                <td className="px-3 py-2 text-right font-data">{formatMoneda(res.data.costoTotalDolares, "Dolares")}</td>
                <td className="px-3 py-2 text-right font-data">{res.data.costoPorHectareaSembradaPesos != null ? formatMoneda(res.data.costoPorHectareaSembradaPesos) : "—"}</td>
                <td className="px-3 py-2 text-right font-data">{res.data.costoPorHectareaSembradaDolares != null ? formatMoneda(res.data.costoPorHectareaSembradaDolares, "Dolares") : "—"}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
      <p className="text-xs text-ink-secondary">Hacé clic en un cultivo para ver sus costos por concepto, como en el formulario de Access.</p>
    </section>
  );
}
