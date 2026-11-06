"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { useToast } from "@/components/ui/Toast";
import { formatFecha, formatMoneda, formatNumero } from "@/lib/format";
import { ApiError } from "@/services/apiClient";
import {
  fetchOrdenesTrabajoCompra,
  fijarOrdenesTrabajoCompra,
  type OrdenTrabajoDeCompra,
  type RepartoContratista,
} from "@/services/comprasApi";

export const ordenesTrabajoKey = (idCompra: number) => ["compras-ordenes-trabajo", idCompra];

const DIAS_PROBABLE = 120;
/** Diferencia normal entre la orden (superficie teórica) y la factura (trabajada + cabeceras). */
const TOLERANCIA = 0.15;
const ha = (v: number) => `${formatNumero(v, { max: 1 })} ha`;
const diasEntre = (desde: string, hasta: string) =>
  Math.round((new Date(hasta).getTime() - new Date(desde).getTime()) / 86_400_000);

/** 048: órdenes de trabajo que cobra esta factura del contratista. Vista compacta: con órdenes vinculadas muestra solo
 *  esas y el reparto; la lista de candidatas aparece al pedir "Cambiar" (o si todavía no hay ninguna). */
export function OrdenesTrabajoPanel({ idCompra }: { idCompra: number }) {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const { data } = useQuery({ queryKey: ordenesTrabajoKey(idCompra), queryFn: () => fetchOrdenesTrabajoCompra(idCompra) });
  const [tildadas, setTildadas] = useState<Set<number>>(new Set());
  const [editando, setEditando] = useState(false);
  const [verTodas, setVerTodas] = useState(false);

  useEffect(() => {
    if (data) setTildadas(new Set(data.ordenes.filter((o) => o.vinculada).map((o) => o.idOrden)));
  }, [data]);

  const guardar = useMutation({
    mutationFn: () => fijarOrdenesTrabajoCompra(idCompra, [...tildadas]),
    onSuccess: () => {
      showToast("Órdenes guardadas: el costo quedó imputado a sus cultivos.", "success");
      setEditando(false);
      qc.invalidateQueries({ queryKey: ordenesTrabajoKey(idCompra) });
      qc.invalidateQueries({ queryKey: ["ordenes"] });
      qc.invalidateQueries({ queryKey: ["resultado-cultivo"] });
    },
    onError: (e) => showToast(e instanceof ApiError ? e.message : "No se pudieron guardar las órdenes.", "danger"),
  });

  const fechaFactura = data?.factura?.fecha ?? null;
  const haFactura = data?.factura?.hectareas ?? null;
  const { probables, resto } = useMemo(() => {
    const ordenes = data?.ordenes ?? [];
    const esProbable = (o: OrdenTrabajoDeCompra) => {
      if (o.vinculada) return true;
      if (!fechaFactura) return false;
      const d = diasEntre(o.fecha, fechaFactura);
      return d >= 0 && d <= DIAS_PROBABLE;
    };
    return { probables: ordenes.filter(esProbable), resto: ordenes.filter((o) => !esProbable(o)) };
  }, [data, fechaFactura]);

  if (!data || !data.esContratista) return null;
  if (data.esNotaCreditoDebito) {
    return (
      <Caja titulo="Órdenes de trabajo">
        <span className="text-ink-secondary">Se imputa igual que su factura: relacionala en Documentos relacionados.</span>
        <Reparto filas={data.reparto} />
      </Caja>
    );
  }
  if (!data.esDocumentoDeLabor) return null;

  const vinculadas = data.ordenes.filter((o) => o.vinculada);
  const seleccionadas = data.ordenes.filter((o) => tildadas.has(o.idOrden));
  const haSel = seleccionadas.reduce((s, o) => s + o.hectareas, 0);
  const cambio = data.ordenes.some((o) => o.vinculada !== tildadas.has(o.idOrden));
  const mostrarLista = editando || vinculadas.length === 0;

  function alternar(id: number) {
    const s = new Set(tildadas);
    if (s.has(id)) s.delete(id);
    else s.add(id);
    setTildadas(s);
  }

  // Vista resumida: ya tiene órdenes y no se está cambiando.
  if (!mostrarLista) {
    return (
      <Caja
        titulo="Órdenes de trabajo"
        accion={
          <SoloLectura>
            <button type="button" onClick={() => setEditando(true)} className="text-finance hover:underline">
              Cambiar
            </button>
          </SoloLectura>
        }
      >
        <span>
          {vinculadas.map((o) => `${formatFecha(o.fecha)} · ${o.labor ?? "Labor"} · ${ha(o.hectareas)}`).join("  |  ")}
        </span>
        <Diferencia haFactura={haFactura} haSel={haSel} />
        <Reparto filas={data.reparto} />
      </Caja>
    );
  }

  return (
    <Caja
      titulo="Órdenes de trabajo que cobra esta factura"
      accion={
        <span className="flex items-center gap-3">
          <Diferencia haFactura={haFactura} haSel={haSel} conFactura />
          {editando && (
            <button type="button" onClick={() => { setEditando(false); setTildadas(new Set(vinculadas.map((o) => o.idOrden))); }}
              className="text-ink-secondary hover:underline">
              Cancelar
            </button>
          )}
          <SoloLectura>
            <button
              type="button"
              onClick={() => guardar.mutate()}
              disabled={!cambio || guardar.isPending}
              className="rounded bg-finance px-3 py-1 text-xs font-medium text-white disabled:opacity-40"
            >
              {guardar.isPending ? "Guardando…" : "Guardar órdenes"}
            </button>
          </SoloLectura>
        </span>
      }
    >
      {data.ordenes.length === 0 ? (
        <span className="text-ink-secondary">Este contratista no tiene órdenes sin facturar.</span>
      ) : (
        <div className="max-h-40 overflow-y-auto rounded border border-border">
          {probables.length === 0 && (
            <div className="px-2 py-1 text-ink-secondary">Sin órdenes sin facturar en los {DIAS_PROBABLE} días previos a la factura.</div>
          )}
          {probables.map((o) => (
            <Fila key={o.idOrden} o={o} tildada={tildadas.has(o.idOrden)} onClick={() => alternar(o.idOrden)} fechaFactura={fechaFactura} haFactura={haFactura} />
          ))}
          {resto.length > 0 && !verTodas && (
            <button type="button" onClick={() => setVerTodas(true)} className="w-full px-2 py-1 text-left text-finance hover:underline">
              Ver órdenes más viejas ({resto.length})
            </button>
          )}
          {verTodas &&
            resto.map((o) => (
              <Fila key={o.idOrden} o={o} tildada={tildadas.has(o.idOrden)} onClick={() => alternar(o.idOrden)} fechaFactura={fechaFactura} haFactura={haFactura} />
            ))}
        </div>
      )}
    </Caja>
  );
}

function Caja({ titulo, accion, children }: { titulo: string; accion?: React.ReactNode; children?: React.ReactNode }) {
  return (
    <section className="mt-2 rounded border border-border bg-surface px-3 py-2 text-xs">
      <div className="mb-1 flex items-center justify-between gap-3">
        <span className="font-medium text-ink-primary">{titulo}</span>
        {accion}
      </div>
      <div className="space-y-1">{children}</div>
    </section>
  );
}

function Diferencia({ haFactura, haSel, conFactura }: { haFactura: number | null; haSel: number; conFactura?: boolean }) {
  if (haFactura == null || haFactura <= 0) return null;
  const dif = haSel - haFactura;
  const grande = haSel > 0 && Math.abs(dif) / haFactura > TOLERANCIA;
  return (
    <span className={grande ? "text-status-warning" : "text-ink-secondary"}>
      {conFactura ? `Factura ${ha(haFactura)} · marcadas ${ha(haSel)}` : `Factura ${ha(haFactura)}`}
      {haSel > 0 && ` · dif. ${dif >= 0 ? "+" : "−"}${ha(Math.abs(dif))}`}
      {grande && " (revisá si falta o sobra alguna orden)"}
    </span>
  );
}

function Fila({ o, tildada, onClick, fechaFactura, haFactura }: {
  o: OrdenTrabajoDeCompra; tildada: boolean; onClick: () => void; fechaFactura: string | null; haFactura: number | null;
}) {
  const dias = fechaFactura ? diasEntre(o.fecha, fechaFactura) : null;
  const parecida = haFactura != null && haFactura > 0 && Math.abs(o.hectareas - haFactura) / haFactura <= TOLERANCIA;
  return (
    <label className={`flex cursor-pointer items-center gap-2 border-b border-border px-2 py-1 last:border-b-0 ${tildada ? "bg-finance-light" : "hover:bg-surface-sunken"}`}>
      <input type="checkbox" checked={tildada} onChange={onClick} />
      <span className="w-20 shrink-0 tabular-nums">{formatFecha(o.fecha)}</span>
      <span className="w-24 shrink-0 text-ink-secondary">
        {dias == null ? "" : dias >= 0 ? `${dias} d antes` : `${-dias} d después`}
      </span>
      <span className="w-44 shrink-0 truncate">{o.labor ?? "Labor"}</span>
      <span className="min-w-0 flex-1 truncate text-ink-secondary" title={o.lotes ? `Lotes ${o.lotes}` : undefined}>
        {o.cultivos ?? ""}
      </span>
      <span className={`w-20 shrink-0 text-right tabular-nums ${parecida ? "font-medium text-status-success" : ""}`}>{ha(o.hectareas)}</span>
    </label>
  );
}

function Reparto({ filas }: { filas: RepartoContratista[] }) {
  const porCultivo = useMemo(() => {
    const m = new Map<string, number>();
    for (const f of filas) {
      const k = `${f.cultivo ?? "Sin cultivo"} ${f.campania ?? ""}`.trim();
      m.set(k, (m.get(k) ?? 0) + f.importe);
    }
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
  }, [filas]);
  if (porCultivo.length === 0) return null;
  return (
    <div className="text-ink-secondary">
      Imputado: {porCultivo.map(([k, v]) => `${k} ${formatMoneda(v)}`).join(" · ")}
    </div>
  );
}
