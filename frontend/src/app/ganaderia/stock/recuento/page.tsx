"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { NumberInput } from "@/components/ui/NumberInput";
import { PageHeader } from "@/components/ui/PageHeader";
import { Segmentos } from "@/components/ui/Segmentos";
import { LoadingState } from "@/components/ui/States";
import { formatNumero } from "@/lib/format";
import { fetchCategoriasHacienda, fetchStock, registrarRecuento } from "@/services/ganaderiaApi";

const hoyIso = () => new Date().toISOString().slice(0, 10);
const SAN_JUSTO = 5671;
type Clave = string; // `${idCategoria}-${dueño}`

/** 052 US2: recuento rápido en el campo (apto celular). Muestra lo esperado y pide motivo si no coincide. */
export default function RecuentoPage() {
  const [fecha, setFecha] = useState(hoyIso());
  const [campo, setCampo] = useState<"1" | "2">("1");
  const [conteo, setConteo] = useState<Record<Clave, number | null>>({});
  const [obs, setObs] = useState("");
  const [resultado, setResultado] = useState<string | null>(null);
  const cats = useQuery({ queryKey: ["ganaderia", "categorias"], queryFn: fetchCategoriasHacienda });
  const esperado = useQuery({ queryKey: ["ganaderia", "stock", fecha, campo, "todos"], queryFn: () => fetchStock(fecha, Number(campo)) });
  const qc = useQueryClient();

  const esp: Record<Clave, number> = {};
  for (const c of esperado.data?.categorias ?? []) esp[`${c.idCategoria}-${c.dueno === "Propia" ? "p" : "t"}`] = c.cabezas;
  useEffect(() => { setConteo({}); setResultado(null); }, [fecha, campo]);

  const filas: { clave: Clave; id: number; nombre: string; terceros: boolean }[] = [];
  for (const c of cats.data?.items ?? []) {
    filas.push({ clave: `${c.id}-p`, id: c.id, nombre: c.nombre, terceros: false });
    if (esp[`${c.id}-t`] != null) filas.push({ clave: `${c.id}-t`, id: c.id, nombre: `${c.nombre} (de terceros)`, terceros: true });
  }
  const contado = (k: Clave) => conteo[k] ?? esp[k] ?? 0;
  const hayDiferencia = filas.some((f) => contado(f.clave) !== (esp[f.clave] ?? 0));
  const guardar = useMutation({
    mutationFn: () => registrarRecuento({
      fecha, establecimiento: Number(campo), origen: "Recuento", observaciones: obs || null,
      detalle: filas.filter((f) => contado(f.clave) > 0).map((f) => ({ categoria: f.id, dueno: f.terceros ? SAN_JUSTO : null, cabezas: contado(f.clave) })),
    }),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ["ganaderia"] });
      setResultado(r.diferencias.length ? `Recuento guardado. Diferencias: ${r.diferencias.map((d) => `${d.categoria} ${d.diferencia > 0 ? "+" : ""}${formatNumero(d.diferencia)}`).join(", ")}` : "Recuento guardado: coincide con lo esperado.");
    },
  });

  return (
    <main className="mx-auto max-w-lg px-4 py-3">
      <PageHeader titulo="Recuento de hacienda" />
      <Link href="/ganaderia/stock" className="mb-3 inline-block text-sm text-finance hover:underline">← Stock de hacienda</Link>
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value || hoyIso())} className="rounded-md border border-border bg-surface px-2 py-1.5" />
        <Segmentos size="sm" etiqueta="Campo" valor={campo} onChange={setCampo} opciones={[{ id: "1", label: "La Herencia" }, { id: "2", label: "San Pedro" }]} />
      </div>
      {cats.isLoading || esperado.isLoading ? <LoadingState rows={8} /> : (
        <>
          <ul className="divide-y divide-border rounded-md border border-border bg-surface">
            {filas.map((f) => {
              const e = esp[f.clave] ?? 0;
              const dif = contado(f.clave) - e;
              return (
                <li key={f.clave} className="flex items-center gap-3 px-3 py-2">
                  <div className="flex-1">
                    <div>{f.nombre}</div>
                    <div className="text-xs text-ink-muted">Esperado {formatNumero(e)}{dif ? <span className={dif < 0 ? "text-status-danger" : "text-status-warning"}> · {dif > 0 ? "+" : ""}{formatNumero(dif)}</span> : null}</div>
                  </div>
                  <NumberInput value={contado(f.clave)} onChange={(v) => setConteo({ ...conteo, [f.clave]: v == null ? 0 : Math.max(0, Math.trunc(v)) })}
                    maxDecimales={0} className="w-24 rounded-md border border-border bg-surface px-2 py-2 text-right text-base" />
                </li>
              );
            })}
          </ul>
          {hayDiferencia && (
            <label className="mt-3 block text-sm">Motivo de la diferencia (obligatorio)
              <textarea value={obs} onChange={(e) => setObs(e.target.value)} rows={2} maxLength={300}
                className="w-full rounded-md border border-border bg-surface px-2 py-1.5" />
            </label>
          )}
          {guardar.isError && <p className="mt-2 text-sm text-status-danger">{(guardar.error as Error).message}</p>}
          {resultado && <p className="mt-2 text-sm text-status-success">{resultado}</p>}
          <button type="button" disabled={guardar.isPending || (hayDiferencia && !obs.trim()) || !!resultado} onClick={() => guardar.mutate()}
            className="mt-3 w-full rounded-md bg-finance px-3 py-2.5 text-white disabled:opacity-50">
            {guardar.isPending ? "Guardando…" : "Guardar recuento"}
          </button>
        </>
      )}
    </main>
  );
}
