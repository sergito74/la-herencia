"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { NumberInput } from "@/components/ui/NumberInput";
import { SideDrawer } from "@/components/ui/SideDrawer";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { formatCantidad, formatFecha } from "@/lib/format";
import {
  anularMovimiento,
  categoriasHacienda,
  obtenerBitacora,
  registrarMovimiento,
  type ContratoFicha,
  type Movimiento,
  type TipoMovimiento,
} from "@/services/pastajeApi";

import { btnPrimario, btnSecundario, ETIQUETA_MOV, inputCls } from "./comunes";

const SIGNO: Partial<Record<TipoMovimiento, string>> = { ingreso: "+", destete: "+", egreso: "−", muerte: "−", faltante: "−" };

export function BitacoraHacienda({ contrato }: { contrato: ContratoFicha }) {
  const cache = useQueryClient();
  const q = useQuery({ queryKey: ["pastaje", "bitacora", contrato.id], queryFn: () => obtenerBitacora(contrato.id) });
  const cats = useQuery({ queryKey: ["pastaje-categorias"], queryFn: categoriasHacienda, staleTime: Infinity });
  const [alta, setAlta] = useState(false);
  const [anular, setAnular] = useState<Movimiento | null>(null);
  const [motivo, setMotivo] = useState("");
  const [form, setForm] = useState({ fecha: "", tipo: "ingreso" as TipoMovimiento, idTipoHacienda: contrato.tarifas[0]?.idTipoHacienda ?? 3, cabezas: null as number | null, numeroDte: "", observacion: "" });
  const [aviso, setAviso] = useState<string | null>(null);

  const refrescar = (afecta: boolean) => {
    cache.invalidateQueries({ queryKey: ["pastaje"] });
    if (afecta) setAviso("El movimiento cae en un mes ya liquidado: la diferencia aparece en Condiciones y se resuelve con un ajuste (ND/NC).");
  };
  const guardar = useMutation({
    mutationFn: () => registrarMovimiento(contrato.id, { ...form, cabezas: form.cabezas ?? 0, numeroDte: form.numeroDte || undefined, observacion: form.observacion || undefined }),
    onSuccess: (r) => {
      setAlta(false);
      setAviso(null);
      if (r.diferencia) setAviso(`Recuento con diferencia de ${r.diferencia > 0 ? "+" : ""}${r.diferencia} cabezas contra el sistema (${r.cabezasSistema}). Registrá el movimiento que lo explica; las cabezas no se ajustan solas.`);
      refrescar(r.afectaLiquidado);
    },
  });
  const baja = useMutation({
    mutationFn: () => anularMovimiento(anular!.id, motivo, anular!.version),
    onSuccess: (r) => {
      setAnular(null);
      setMotivo("");
      refrescar(r.afectaLiquidado);
    },
  });

  if (q.isLoading) return <LoadingState />;
  if (q.isError) return <ErrorState message={(q.error as Error).message} onRetry={() => q.refetch()} />;
  const b = q.data!;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm">
          <span className="text-ink-secondary">Cabezas vigentes hoy: </span>
          <span className="font-data font-semibold">
            {b.cabezasActuales.length ? b.cabezasActuales.map((x) => `${formatCantidad(x.cabezas)} ${x.categoria}`).join(" · ") : "sin hacienda"}
          </span>
        </p>
        {contrato.estado === "vigente" && (
          <SoloLectura>
            <button className={btnPrimario} onClick={() => setAlta(true)}>+ Registrar movimiento</button>
          </SoloLectura>
        )}
      </div>
      {aviso && <p role="status" className="rounded-sm bg-status-warning-bg px-3 py-2 text-sm text-status-warning">⚠ {aviso}</p>}
      {b.movimientos.length === 0 ? (
        <EmptyState message="Todavía no hay movimientos. Registrá el ingreso de la hacienda con su DTe." />
      ) : (
        <ol className="relative space-y-3 border-l border-border pl-5">
          {b.movimientos.map((m) => (
            <li key={m.id} className={m.estado === "anulado" ? "text-ink-secondary" : ""}>
              <span className="absolute -left-1.5 mt-1.5 h-3 w-3 rounded-full border border-border bg-surface" aria-hidden />
              <p className={m.estado === "anulado" ? "line-through" : ""}>
                <span className="font-data">{formatFecha(m.fecha)}</span> · <strong>{ETIQUETA_MOV[m.tipo]}</strong>{" "}
                <span className="font-data">{SIGNO[m.tipo] ?? ""}{formatCantidad(m.cabezas)}</span> {m.categoria}
                {m.numeroDte && <> · DTe {m.numeroDte}</>}
                {m.tipo === "recuento" && m.cabezasSistema !== null && (
                  <> · sistema {formatCantidad(m.cabezasSistema)} {m.cabezas !== m.cabezasSistema && <span className="text-status-warning">(diferencia {m.cabezas - m.cabezasSistema > 0 ? "+" : ""}{m.cabezas - m.cabezasSistema})</span>}</>
                )}
              </p>
              <p className="text-xs text-ink-secondary">
                {m.observacion && <>{m.observacion} · </>}cargó {m.creadoPor}
                {m.estado === "anulado" && <> · anulado: {m.motivoAnulacion}</>}
                {m.estado === "vigente" && (
                  <SoloLectura>
                    {" · "}
                    <button className="underline" onClick={() => setAnular(m)}>Anular</button>
                  </SoloLectura>
                )}
              </p>
            </li>
          ))}
        </ol>
      )}
      <p className="text-xs text-ink-secondary">El día de ingreso se cobra; el día de egreso, muerte o faltante no. Las crías cobran desde el destete.</p>

      <SideDrawer open={alta} onClose={() => setAlta(false)} title="Registrar movimiento de hacienda">
        <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); guardar.mutate(); }}>
          <label className="block text-sm">
            Tipo
            <select autoFocus className={inputCls} value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value as TipoMovimiento })}>
              {Object.entries(ETIQUETA_MOV).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </label>
          <label className="block text-sm">
            Fecha
            <input type="date" required className={inputCls} value={form.fecha} onChange={(e) => setForm({ ...form, fecha: e.target.value })} />
          </label>
          <label className="block text-sm">
            Categoría
            <select className={inputCls} value={form.idTipoHacienda} onChange={(e) => setForm({ ...form, idTipoHacienda: Number(e.target.value) })}>
              {cats.data?.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
            </select>
          </label>
          <label className="block text-sm">
            {form.tipo === "recuento" ? "Cabezas contadas" : "Cabezas"}
            <NumberInput className={inputCls} value={form.cabezas} maxDecimales={0} onChange={(v) => setForm({ ...form, cabezas: v })} required />
          </label>
          {(form.tipo === "ingreso" || form.tipo === "egreso") && (
            <label className="block text-sm">
              Número de DTe
              <input className={inputCls} maxLength={40} value={form.numeroDte} onChange={(e) => setForm({ ...form, numeroDte: e.target.value })} />
            </label>
          )}
          <label className="block text-sm">
            Observación
            <input className={inputCls} maxLength={400} value={form.observacion} onChange={(e) => setForm({ ...form, observacion: e.target.value })} />
          </label>
          {guardar.error && <p role="alert" className="text-sm text-status-danger">{(guardar.error as Error).message}</p>}
          <button className={btnPrimario} disabled={!form.fecha || !form.cabezas || guardar.isPending}>Guardar</button>
        </form>
      </SideDrawer>
      <SideDrawer open={anular !== null} onClose={() => setAnular(null)} title="Anular movimiento">
        <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); baja.mutate(); }}>
          <p className="text-sm">{anular && `${ETIQUETA_MOV[anular.tipo]} de ${anular.cabezas} ${anular.categoria} del ${formatFecha(anular.fecha)}`}</p>
          <label className="block text-sm">
            Motivo
            <input autoFocus required className={inputCls} value={motivo} onChange={(e) => setMotivo(e.target.value)} />
          </label>
          {baja.error && <p role="alert" className="text-sm text-status-danger">{(baja.error as Error).message}</p>}
          <button className={btnSecundario} disabled={!motivo || baja.isPending}>Anular</button>
        </form>
      </SideDrawer>
    </div>
  );
}
