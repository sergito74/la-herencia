"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { NumberInput } from "@/components/ui/NumberInput";
import { PageHeader } from "@/components/ui/PageHeader";
import { SideDrawer } from "@/components/ui/SideDrawer";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatNumero } from "@/lib/format";
import { apiDelete, apiGet, apiPut } from "@/services/apiClient";

type Valor = string | number | boolean | null;
type Fila = Record<string, Valor> & { id: number };
interface Campo { key: string; label: string; tipo: "num" | "int" | "texto" | "opcion" | "si_no"; opciones: string | null; edita: boolean; alta: boolean; max: number | null }
interface Opcion { id: string | number; nombre: string }
interface Seccion { seccion: string; titulo: string; ayuda: string; alta: boolean; campos: Campo[]; opciones: Record<string, Opcion[]>; filas: Fila[] }

const BORRABLES = new Set(["alias", "ajustes_superficie", "valuacion"]);
const inputCls = "w-full rounded-md border border-border bg-surface px-2 py-1 text-sm";

/** 052 T025: parámetros del módulo ganadero, por nombre (sin ids). */
export default function ConfiguracionGanaderaPage() {
  const qs = useQuery({ queryKey: ["ganaderia", "configuracion"],
    queryFn: () => apiGet<{ secciones: { seccion: string; titulo: string }[] }>("/api/ganaderia/configuracion") });
  const [actual, setActual] = useState("categorias");
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Configuración ganadera"
        ayuda="Parámetros que usan el resultado, el stock y la valuación. Al guardar se recalcula el resultado." />
      <div className="flex gap-4">
        <nav className="w-60 shrink-0 space-y-0.5">
          {(qs.data?.secciones ?? []).map((s) => (
            <button key={s.seccion} type="button" onClick={() => setActual(s.seccion)}
              className={`block w-full rounded-md px-2.5 py-1.5 text-left text-sm ${actual === s.seccion ? "bg-surface-sunken font-semibold" : "hover:bg-surface-sunken"}`}>
              {s.titulo}
            </button>
          ))}
        </nav>
        <div className="min-w-0 flex-1"><SeccionTabla nombre={actual} /></div>
      </div>
    </main>
  );
}

function mostrar(c: Campo, v: Valor, ops: Record<string, Opcion[]>) {
  if (v === null || v === undefined || v === "") return "—";
  if (c.tipo === "opcion") return ops[c.opciones ?? ""]?.find((o) => String(o.id) === String(v))?.nombre ?? "—";
  if (c.tipo === "si_no") return v ? "Sí" : "No";
  if (c.tipo === "num") return formatNumero(Number(v), { max: 3 });
  return String(v);
}

function SeccionTabla({ nombre }: { nombre: string }) {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["ganaderia", "configuracion", nombre], queryFn: () => apiGet<Seccion>(`/api/ganaderia/configuracion/${nombre}`) });
  const [editando, setEditando] = useState<Fila | "nueva" | null>(null);
  const borrar = useMutation({
    mutationFn: (id: number) => apiDelete(`/api/ganaderia/configuracion/${nombre}/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ganaderia"] }),
  });
  if (q.isLoading) return <LoadingState rows={6} />;
  if (q.isError || !q.data) return <ErrorState message="No se pudo leer la configuración." onRetry={() => q.refetch()} />;
  const s = q.data;
  return (
    <section>
      <div className="mb-2 flex items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold">{s.titulo}</h2>
          <p className="text-sm text-ink-secondary">{s.ayuda}</p>
        </div>
        {s.alta && (
          <SoloLectura>
            <button type="button" onClick={() => setEditando("nueva")} className="rounded-md bg-finance px-2.5 py-1 text-sm text-white hover:opacity-90">Agregar</button>
          </SoloLectura>
        )}
      </div>
      <div className="overflow-auto rounded-md border border-border bg-surface">
        <table className="min-w-full text-sm">
          <thead><tr className="border-b border-border text-left text-ink-secondary">
            {s.campos.map((c) => <th key={c.key} className={`px-3 py-2 font-medium ${c.tipo === "num" || c.tipo === "int" ? "text-right" : ""}`}>{c.label}</th>)}
            <th />
          </tr></thead>
          <tbody>
            {!s.filas.length && <tr><td colSpan={s.campos.length + 1} className="px-3 py-3 text-ink-muted">Sin filas.</td></tr>}
            {s.filas.map((f) => (
              <tr key={f.id} className="border-b border-border/60">
                {s.campos.map((c) => (
                  <td key={c.key} className={`px-3 py-1 ${c.tipo === "num" || c.tipo === "int" ? "text-right font-data" : ""}`}>{mostrar(c, f[c.key], s.opciones)}</td>
                ))}
                <td className="whitespace-nowrap px-3 py-1 text-right">
                  <SoloLectura>
                    <button type="button" onClick={() => setEditando(f)} className="text-finance hover:underline">Editar</button>
                    {BORRABLES.has(nombre) && (
                      <button type="button" disabled={borrar.isPending} onClick={() => { if (window.confirm("¿Borrar esta fila?")) borrar.mutate(f.id); }}
                        className="ml-3 text-status-danger hover:underline">Borrar</button>
                    )}
                  </SoloLectura>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {editando && <Formulario seccion={s} fila={editando === "nueva" ? null : editando} onClose={() => setEditando(null)} />}
    </section>
  );
}

function Formulario({ seccion, fila, onClose }: { seccion: Seccion; fila: Fila | null; onClose: () => void }) {
  const qc = useQueryClient();
  const campos = seccion.campos.filter((c) => (fila ? true : c.alta));
  const [v, setV] = useState<Record<string, Valor>>(() => Object.fromEntries(campos.map((c) => [c.key, fila?.[c.key] ?? null])));
  const [error, setError] = useState<string | null>(null);
  const m = useMutation({
    mutationFn: () => apiPut(`/api/ganaderia/configuracion/${seccion.seccion}`, {
      id: fila?.id ?? null, valores: Object.fromEntries(campos.filter((c) => (fila ? c.edita : c.alta)).map((c) => [c.key, v[c.key]])) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["ganaderia"] }); onClose(); },
    onError: (e) => setError(e instanceof Error ? e.message : "No se pudo guardar."),
  });
  const set = (k: string, x: Valor) => setV((p) => ({ ...p, [k]: x }));
  return (
    <SideDrawer open onClose={onClose} title={`${fila ? "Editar" : "Agregar"}: ${seccion.titulo}`}>
      {campos.map((c) => {
        const bloqueado = fila ? !c.edita : false;
        return (
          <label key={c.key} className="mb-2 block text-sm">{c.label}
            {bloqueado ? <div className="py-1 font-medium">{mostrar(c, v[c.key], seccion.opciones)}</div>
              : c.tipo === "opcion" ? (
                <select value={v[c.key] == null ? "" : String(v[c.key])} onChange={(e) => set(c.key, e.target.value || null)} className={inputCls}>
                  <option value="">—</option>
                  {(seccion.opciones[c.opciones ?? ""] ?? []).map((o) => <option key={o.id} value={String(o.id)}>{o.nombre}</option>)}
                </select>
              ) : c.tipo === "si_no" ? (
                <input type="checkbox" checked={Boolean(v[c.key])} onChange={(e) => set(c.key, e.target.checked)} className="ml-2" />
              ) : c.tipo === "texto" ? (
                <input value={v[c.key] == null ? "" : String(v[c.key])} maxLength={c.max ?? undefined}
                  onChange={(e) => set(c.key, e.target.value)} className={inputCls} />
              ) : (
                <NumberInput value={v[c.key] == null ? null : Number(v[c.key])} onChange={(x) => set(c.key, x)} className={inputCls} />
              )}
          </label>
        );
      })}
      {error && <p className="mb-2 text-sm text-status-danger">{error}</p>}
      <button type="button" disabled={m.isPending} onClick={() => m.mutate()}
        className="rounded-md bg-finance px-3 py-1.5 text-sm text-white disabled:opacity-50">Guardar</button>
    </SideDrawer>
  );
}
