"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { ApiError } from "@/services/apiClient";
import { corregirHectareas, fetchRepartoCultivos, type OrdenDetalle } from "@/services/ordenesApi";
import { formatCantidad } from "@/lib/format";
import { NumberInput } from "@/components/ui/NumberInput";
import { useToast } from "@/components/ui/Toast";

/** Hectáreas realmente aplicadas por lote (04/11/2026): cambia solo a qué cultivo va cada insumo; las cantidades,
 * el stock y los ajustes del recuento no se tocan. */
export function HectareasAplicadasPanel({ orden, onGuardada }: { orden: OrdenDetalle; onGuardada: () => void }) {
  const { showToast } = useToast();
  const qc = useQueryClient();
  const reparto = useQuery({ queryKey: ["orden-reparto", orden.idOrden], queryFn: () => fetchRepartoCultivos(orden.idOrden) });

  const lotes = useMemo(() => {
    const m = new Map<number, { idLote: number; lote: string | null; cultivo: string | null; superficie: number }>();
    for (const r of orden.insumos)
      for (const d of r.distribuciones)
        if (!m.has(d.idLote)) m.set(d.idLote, { idLote: d.idLote, lote: d.lote, cultivo: d.cultivo, superficie: d.superficie });
    return [...m.values()].sort((a, b) => (a.cultivo ?? "").localeCompare(b.cultivo ?? "") || (a.lote ?? "").localeCompare(b.lote ?? ""));
  }, [orden]);

  const [editando, setEditando] = useState(false);
  const [valores, setValores] = useState<Record<number, number | null>>({});
  const [guardando, setGuardando] = useState(false);

  const valor = (id: number, original: number) => (id in valores ? valores[id] : original);
  const porCultivo = useMemo(() => {
    const t = new Map<string, number>();
    for (const l of lotes) t.set(l.cultivo ?? "—", (t.get(l.cultivo ?? "—") ?? 0) + (valor(l.idLote, l.superficie) ?? 0));
    return [...t.entries()];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lotes, valores]);

  async function guardar() {
    if (lotes.some((l) => valor(l.idLote, l.superficie) == null)) {
      showToast("Completá las hectáreas de todos los lotes.", "danger");
      return;
    }
    setGuardando(true);
    try {
      await corregirHectareas(orden.idOrden, lotes.map((l) => ({ idLote: l.idLote, superficie: valor(l.idLote, l.superficie) ?? 0 })));
      showToast("Hectáreas guardadas: el reparto de insumos entre cultivos se actualizó.", "success");
      setEditando(false);
      setValores({});
      qc.invalidateQueries({ queryKey: ["orden-reparto", orden.idOrden] });
      onGuardada();
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "No se pudieron guardar las hectáreas.", "danger");
    } finally {
      setGuardando(false);
    }
  }

  const filas = reparto.data?.repartoPorCultivo ?? [];
  const cultivos = [...new Set(filas.map((f) => f.cultivo ?? "—"))];

  return (
    <section className="mt-6">
      <div className="flex items-baseline justify-between">
        <h2 className="text-lg font-medium">Hectáreas aplicadas</h2>
        {!editando && (
          <button type="button" onClick={() => setEditando(true)} className="text-sm text-finance underline">
            Corregir hectáreas aplicadas
          </button>
        )}
      </div>
      <p className="text-sm text-ink-secondary">
        Si en algún lote se aplicó menos (o más) superficie, cargá lo real: el insumo usado se reparte de nuevo entre los
        cultivos. Las cantidades retiradas y el stock no cambian.
      </p>

      <table className="mt-2 text-sm">
        <thead>
          <tr className="text-left text-ink-secondary">
            <th className="pr-6 font-normal">Cultivo</th>
            <th className="pr-6 font-normal">Lote</th>
            <th className="pr-2 text-right font-normal">Hectáreas</th>
          </tr>
        </thead>
        <tbody>
          {lotes.map((l) => (
            <tr key={l.idLote}>
              <td className="pr-6">{l.cultivo}</td>
              <td className="pr-6">{l.lote}</td>
              <td className="py-0.5 text-right">
                {editando ? (
                  <NumberInput className="w-24 rounded border border-border px-2 py-0.5 text-right" maxDecimales={2}
                    value={valor(l.idLote, l.superficie)} onChange={(v) => setValores((s) => ({ ...s, [l.idLote]: v }))} />
                ) : (
                  formatCantidad(l.superficie)
                )}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          {porCultivo.map(([c, ha]) => (
            <tr key={c} className="text-ink-secondary">
              <td className="pr-6">Total {c}</td>
              <td />
              <td className="text-right">{formatCantidad(ha)}</td>
            </tr>
          ))}
        </tfoot>
      </table>
      {editando && (
        <div className="mt-2 flex gap-2">
          <button type="button" onClick={guardar} disabled={guardando} className="rounded bg-finance px-3 py-1 text-sm text-white disabled:opacity-50">
            Guardar
          </button>
          <button type="button" onClick={() => { setEditando(false); setValores({}); }} className="rounded border border-border px-3 py-1 text-sm">
            Cancelar
          </button>
        </div>
      )}

      {filas.length > 0 && (
        <div className="mt-4 overflow-x-auto">
          <h3 className="text-sm font-medium">Insumo usado por cultivo (incluye el ajuste del recuento)</h3>
          <table className="mt-1 text-sm">
            <thead>
              <tr className="text-left text-ink-secondary">
                <th className="pr-6 font-normal">Insumo</th>
                {cultivos.map((c) => <th key={c} className="pr-4 text-right font-normal">{c}</th>)}
              </tr>
            </thead>
            <tbody>
              {[...new Set(filas.map((f) => f.producto))].map((p) => (
                <tr key={p ?? ""}>
                  <td className="pr-6">{p}</td>
                  {cultivos.map((c) => {
                    const f = filas.find((x) => x.producto === p && (x.cultivo ?? "—") === c);
                    return <td key={c} className="pr-4 text-right">{f ? `${formatCantidad(f.cantidad)} ${f.unidad ?? ""}` : ""}</td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
