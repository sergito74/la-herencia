"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { NumberInput } from "@/components/ui/NumberInput";
import { PageHeader } from "@/components/ui/PageHeader";
import { Segmentos } from "@/components/ui/Segmentos";
import { SideDrawer } from "@/components/ui/SideDrawer";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { formatFecha, formatNumero } from "@/lib/format";
import { ApiError } from "@/services/apiClient";
import {
  anularMovimiento,
  fetchCategoriasHacienda,
  fetchMovimientos,
  fetchStock,
  registrarMovimiento,
  type DuenoFiltro,
  type MovimientoHacienda,
  type MovimientoNuevo,
} from "@/services/ganaderiaApi";

const hoyIso = () => new Date().toISOString().slice(0, 10);
const TIPOS = [
  { id: "Nacimiento", label: "Nacimiento" }, { id: "Compra", label: "Compra" }, { id: "Muerte", label: "Muerte" },
  { id: "Consumo", label: "Consumo propio" }, { id: "CambioCategoria", label: "Cambio de categoría" },
  { id: "Traslado", label: "Traslado entre campos" }, { id: "PastajeEntrada", label: "Entrada de pastaje" },
  { id: "PastajeSalida", label: "Salida de pastaje" }, { id: "AjusteRecuento", label: "Ajuste de recuento" },
];
const NOMBRE_TIPO: Record<string, string> = { Venta: "Venta", ...Object.fromEntries(TIPOS.map((t) => [t.id, t.label])) };
const CAMPOS = [{ id: "1", label: "La Herencia" }, { id: "2", label: "San Pedro" }];
const SAN_JUSTO = 5671; // dueño de la hacienda en pastaje (contrato vigente)
const inputCls = "w-full rounded-md border border-border bg-surface px-2 py-1 text-sm";

/** 052 US2: existencia de hacienda a una fecha (recuento + movimientos) y movimientos del stock. */
export default function StockHaciendaPage() {
  const [fecha, setFecha] = useState(hoyIso());
  const [campo, setCampo] = useState<"todos" | "1" | "2">("todos");
  const [dueno, setDueno] = useState<DuenoFiltro>("todos");
  const [nuevo, setNuevo] = useState(false);
  const [pagina, setPagina] = useState(1);
  const est = campo === "todos" ? undefined : Number(campo);
  const qs = useQuery({ queryKey: ["ganaderia", "stock", fecha, campo, dueno], queryFn: () => fetchStock(fecha, est, dueno) });
  const qm = useQuery({ queryKey: ["ganaderia", "movimientos", campo], queryFn: () => fetchMovimientos(undefined, undefined, undefined, est) });
  const qc = useQueryClient();
  const anular = useMutation({
    mutationFn: ({ id, motivo }: { id: number; motivo: string }) => anularMovimiento(id, motivo),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ganaderia"] }),
  });
  const [anulando, setAnulando] = useState<MovimientoHacienda | null>(null);

  const columnas: DataTableColumn<MovimientoHacienda>[] = useMemo(() => [
    { key: "fecha", header: "Fecha", numeric: true, width: "w-24", render: (m) => formatFecha(m.fecha), sortValue: (m) => m.fecha },
    { key: "tipo", header: "Movimiento", width: "w-40", render: (m) => NOMBRE_TIPO[m.tipo] ?? m.tipo },
    { key: "cat", header: "Categoría", render: (m) => m.categoriaDestinoNombre ? `${m.categoriaNombre} → ${m.categoriaDestinoNombre}` : m.categoriaNombre },
    { key: "cab", header: "Cabezas", align: "right", numeric: true, width: "w-20", render: (m) => formatNumero(m.cabezas) },
    { key: "kg", header: "Kg", align: "right", numeric: true, width: "w-24",
      render: (m) => m.kg == null ? "—" : `${formatNumero(m.kg, { max: 0 })}${m.kgEstimado ? " (est.)" : ""}` },
    { key: "dueno", header: "Dueño", width: "w-44", render: (m) => m.duenoNombre },
    { key: "campo", header: "Campo", width: "w-28", render: (m) => m.establecimientoNombre },
    { key: "fuente", header: "Origen", wrap: true,
      render: (m) => m.enlace ? <Link className="text-finance hover:underline" href={m.enlace}>{m.fuente}</Link> : (m.motivo ?? m.fuente) },
  ], []);
  const movs = qm.data?.items ?? [];

  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Stock de hacienda"
        ayuda="Existencia por categoría a la fecha elegida: el último recuento del campo más los movimientos posteriores. Las ventas descuentan solas desde Ventas de hacienda.">
        <SoloLectura>
          <div className="flex gap-2">
            <Link href="/ganaderia/stock/recuento" className="rounded-md border border-border px-2.5 py-1 text-sm hover:bg-surface-sunken">Cargar recuento</Link>
            <button type="button" onClick={() => setNuevo(true)} className="rounded-md bg-finance px-2.5 py-1 text-sm text-white hover:opacity-90">
              Registrar movimiento
            </button>
          </div>
        </SoloLectura>
      </PageHeader>
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-sm text-ink-secondary">Fecha
          <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value || hoyIso())} className="rounded-md border border-border bg-surface px-2 py-1 text-sm" />
        </label>
        <Segmentos size="sm" etiqueta="Campo" valor={campo} onChange={(v) => { setCampo(v); setPagina(1); }}
          opciones={[{ id: "todos", label: "Todos los campos" }, ...CAMPOS] as { id: "todos" | "1" | "2"; label: string }[]} />
        <Segmentos size="sm" etiqueta="Dueño" valor={dueno} onChange={setDueno}
          opciones={[{ id: "todos", label: "Toda la hacienda" }, { id: "propia", label: "Propia" }, { id: "terceros", label: "De terceros" }]} />
      </div>

      {qs.isLoading ? <LoadingState rows={8} />
        : qs.isError ? <ErrorState message="No se pudo calcular el stock." onRetry={() => qs.refetch()} />
        : !qs.data?.categorias.length ? <EmptyState message="No hay hacienda a esa fecha." />
        : (
          <section className="mb-5">
            <p className="mb-2 text-sm text-ink-secondary">
              {qs.data.bases.map((b) => `${b.establecimiento}: último recuento ${formatFecha(b.fecha)} (${b.origen.toLowerCase()})`).join(" · ")}
            </p>
            <div className="overflow-auto rounded-md border border-border bg-surface">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-border text-left text-ink-secondary">
                  <th className="px-3 py-2 font-medium">Campo</th><th className="px-3 py-2 font-medium">Dueño</th>
                  <th className="px-3 py-2 font-medium">Categoría</th><th className="px-3 py-2 text-right font-medium">Cabezas</th>
                  <th className="px-3 py-2 text-right font-medium">Kg (estimados)</th><th className="px-3 py-2 text-right font-medium">EV</th>
                </tr></thead>
                <tbody>
                  {qs.data.categorias.map((c) => (
                    <tr key={`${c.idEstablecimiento}-${c.dueno}-${c.idCategoria}`} className="border-b border-border/60">
                      <td className="px-3 py-1">{c.establecimiento}</td>
                      <td className="px-3 py-1">{c.dueno === "Propia" ? "Propia" : c.duenoNombre ?? "De terceros"}</td>
                      <td className="px-3 py-1">{c.categoria}</td>
                      <td className={`px-3 py-1 text-right font-data ${c.cabezas < 0 ? "text-status-danger" : ""}`}>{formatNumero(c.cabezas)}</td>
                      <td className="px-3 py-1 text-right font-data">{formatNumero(c.kg, { max: 0 })}</td>
                      <td className="px-3 py-1 text-right font-data">{formatNumero(c.ev, { max: 1 })}</td>
                    </tr>
                  ))}
                  <tr className="bg-surface-sunken font-semibold">
                    <td className="px-3 py-1.5" colSpan={3}>Total</td>
                    <td className="px-3 py-1.5 text-right font-data">{formatNumero(qs.data.totalCabezas)}</td><td />
                    <td className="px-3 py-1.5 text-right font-data">{formatNumero(qs.data.totalEv, { max: 1 })}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            {qs.data.categorias.some((c) => c.cabezas < 0) && (
              <p className="mt-2 text-sm text-status-danger">Hay categorías en negativo: salió más hacienda que la contada. Falta un recuento o un movimiento (nacimiento, cambio de categoría).</p>
            )}
            {qs.data.sinExplicar.length > 0 && (
              <p className="mt-2 text-xs text-ink-muted">
                Diferencia del último recuento contra lo esperado (nacimientos, muertes y cambios de categoría sin registrar):{" "}
                {qs.data.sinExplicar.map((s) => `${s.establecimiento} ${s.categoria} ${s.diferencia > 0 ? "+" : ""}${formatNumero(s.diferencia)}`).join(" · ")}
              </p>
            )}
          </section>
        )}

      <h2 className="mb-2 text-base font-semibold">Movimientos</h2>
      {qm.isLoading ? <LoadingState rows={6} /> : (
        <DataTable columns={columnas} rows={movs.slice((pagina - 1) * 50, pagina * 50)} keyField={(m) => m.id}
          emptyMessage="No hay movimientos." page={pagina} pageSize={50} total={movs.length} onPageChange={setPagina}
          layout="fixed" rowClassName={(m) => (m.anulado ? "line-through text-ink-muted" : undefined)}
          rowActions={(m) => (m.anulado || m.idVenta ? [] : [{ label: "Anular", peligro: true, onClick: () => setAnulando(m) }])} />
      )}

      {nuevo && <NuevoMovimiento onClose={() => setNuevo(false)} />}
      {anulando && (
        <MotivoDrawer titulo="Anular movimiento" onClose={() => setAnulando(null)} pendiente={anular.isPending}
          onConfirm={(motivo) => anular.mutate({ id: anulando.id, motivo }, { onSuccess: () => setAnulando(null) })} />
      )}
    </main>
  );
}

function MotivoDrawer({ titulo, onClose, onConfirm, pendiente }: {
  titulo: string; onClose: () => void; onConfirm: (motivo: string) => void; pendiente: boolean;
}) {
  const [motivo, setMotivo] = useState("");
  return (
    <SideDrawer open onClose={onClose} title={titulo}>
      <label className="block text-sm">Motivo
        <textarea value={motivo} onChange={(e) => setMotivo(e.target.value)} rows={3} className={inputCls} />
      </label>
      <button type="button" disabled={!motivo.trim() || pendiente} onClick={() => onConfirm(motivo.trim())}
        className="mt-3 rounded-md bg-status-danger px-3 py-1.5 text-sm text-white disabled:opacity-50">Anular</button>
    </SideDrawer>
  );
}

function NuevoMovimiento({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const cats = useQuery({ queryKey: ["ganaderia", "categorias"], queryFn: fetchCategoriasHacienda });
  const [m, setM] = useState<MovimientoNuevo>({ fecha: hoyIso(), tipo: "Nacimiento", categoria: 0, cabezas: 0, establecimiento: 1 });
  const [terceros, setTerceros] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const guardar = useMutation({
    mutationFn: (confirmar: boolean) => registrarMovimiento({ ...m, dueno: terceros ? SAN_JUSTO : null, confirmar }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["ganaderia"] }); onClose(); },
    onError: (e) => {
      if (e instanceof ApiError && e.status === 409) setAviso("Con este movimiento la existencia de la categoría queda negativa. ¿Guardarlo igual?");
      else setError(e instanceof Error ? e.message : "No se pudo guardar");
    },
  });
  const set = (p: Partial<MovimientoNuevo>) => { setM({ ...m, ...p }); setAviso(null); setError(null); };
  const opcionesCat = (cats.data?.items ?? []).map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>);
  const valido = m.categoria > 0 && m.cabezas !== 0 && (m.tipo !== "AjusteRecuento" || !!m.motivo?.trim())
    && (m.tipo !== "CambioCategoria" || !!m.categoriaDestino) && (m.tipo !== "Traslado" || !!m.establecimientoDestino);

  return (
    <SideDrawer open onClose={onClose} title="Registrar movimiento">
      <div className="space-y-3 text-sm">
        <label className="block">Movimiento
          <select value={m.tipo} onChange={(e) => set({ tipo: e.target.value })} className={inputCls}>
            {TIPOS.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
          </select>
        </label>
        <label className="block">Fecha
          <input type="date" value={m.fecha} onChange={(e) => set({ fecha: e.target.value })} className={inputCls} />
        </label>
        <label className="block">Campo
          <select value={m.establecimiento} onChange={(e) => set({ establecimiento: Number(e.target.value) })} className={inputCls}>
            {CAMPOS.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
          </select>
        </label>
        <label className="block">Categoría
          <select value={m.categoria} onChange={(e) => set({ categoria: Number(e.target.value) })} className={inputCls}>
            <option value={0}>Elegí…</option>{opcionesCat}
          </select>
        </label>
        {m.tipo === "CambioCategoria" && (
          <label className="block">Pasa a
            <select value={m.categoriaDestino ?? 0} onChange={(e) => set({ categoriaDestino: Number(e.target.value) || null })} className={inputCls}>
              <option value={0}>Elegí…</option>{opcionesCat}
            </select>
          </label>
        )}
        {m.tipo === "Traslado" && (
          <label className="block">Campo de destino
            <select value={m.establecimientoDestino ?? 0} onChange={(e) => set({ establecimientoDestino: Number(e.target.value) || null })} className={inputCls}>
              <option value={0}>Elegí…</option>{CAMPOS.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
            </select>
          </label>
        )}
        <label className="block">Cabezas{m.tipo === "AjusteRecuento" ? " (negativo si faltan)" : ""}
          <NumberInput value={m.cabezas || null} onChange={(v) => set({ cabezas: Math.trunc(v ?? 0) })} maxDecimales={0} className={inputCls} />
        </label>
        <label className="block">Kg (opcional)
          <NumberInput value={m.kg ?? null} onChange={(v) => set({ kg: v })} maxDecimales={1} className={inputCls} />
        </label>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={terceros} onChange={(e) => setTerceros(e.target.checked)} />
          Hacienda de terceros en pastaje (Ganadera San Justo)
        </label>
        {m.tipo === "Muerte" && (
          <label className="block">Causa
            <input value={m.causa ?? ""} onChange={(e) => set({ causa: e.target.value })} maxLength={40} className={inputCls} />
          </label>
        )}
        <label className="block">Motivo / observación{m.tipo === "AjusteRecuento" ? " (obligatorio)" : ""}
          <textarea value={m.motivo ?? ""} onChange={(e) => set({ motivo: e.target.value })} rows={2} maxLength={300} className={inputCls} />
        </label>
        {error && <p className="text-status-danger">{error}</p>}
        {aviso ? (
          <div className="rounded-md border border-status-warning p-2">
            <p>{aviso}</p>
            <button type="button" onClick={() => guardar.mutate(true)} className="mt-2 rounded-md border border-border px-2.5 py-1">Guardar igual</button>
          </div>
        ) : (
          <button type="button" disabled={!valido || guardar.isPending} onClick={() => guardar.mutate(false)}
            className="rounded-md bg-finance px-3 py-1.5 text-white disabled:opacity-50">{guardar.isPending ? "Guardando…" : "Guardar"}</button>
        )}
      </div>
    </SideDrawer>
  );
}
