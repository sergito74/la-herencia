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
/** Diferencia de superficie que se considera normal entre la orden (teórica) y la factura (trabajada + cabeceras). */
const TOLERANCIA = 0.15;
const ha = (v: number) => `${formatNumero(v, { max: 1 })} ha`;

function diasEntre(desde: string, hasta: string) {
  return Math.round((new Date(hasta).getTime() - new Date(desde).getTime()) / 86_400_000);
}

/** 048: órdenes de trabajo que originó esta factura del contratista. Al guardar, el costo se reparte solo por la
 *  superficie de las órdenes (cultivo/campaña). Las NC/ND siguen a su factura. */
export function OrdenesTrabajoPanel({ idCompra }: { idCompra: number }) {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const { data } = useQuery({ queryKey: ordenesTrabajoKey(idCompra), queryFn: () => fetchOrdenesTrabajoCompra(idCompra) });
  const [tildadas, setTildadas] = useState<Set<number>>(new Set());
  const [verTodas, setVerTodas] = useState(false);

  useEffect(() => {
    if (data) setTildadas(new Set(data.ordenes.filter((o) => o.vinculada).map((o) => o.idOrden)));
  }, [data]);

  const guardar = useMutation({
    mutationFn: () => fijarOrdenesTrabajoCompra(idCompra, [...tildadas]),
    onSuccess: () => {
      showToast("Listo: el costo de la factura quedó imputado a los cultivos de esas órdenes.", "success");
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
      if (o.tieneOtraFactura || !fechaFactura) return false;
      const d = diasEntre(o.fecha, fechaFactura);
      return d >= 0 && d <= DIAS_PROBABLE;
    };
    return { probables: ordenes.filter(esProbable), resto: ordenes.filter((o) => !esProbable(o)) };
  }, [data, fechaFactura]);

  if (!data || !data.esContratista) return null;

  if (data.esNotaCreditoDebito) {
    return (
      <Tarjeta titulo="Órdenes de trabajo" subtitulo="Esta nota se imputa igual que su factura: relacionala arriba, en Documentos relacionados.">
        <Reparto filas={data.reparto} />
      </Tarjeta>
    );
  }
  if (!data.esDocumentoDeLabor) return null;

  const seleccionadas = data.ordenes.filter((o) => tildadas.has(o.idOrden));
  const haSel = seleccionadas.reduce((s, o) => s + o.hectareas, 0);
  const cambio = data.ordenes.some((o) => o.vinculada !== tildadas.has(o.idOrden));
  const coincide = (h: number) => haFactura != null && haFactura > 0 && Math.abs(h - haFactura) / haFactura <= TOLERANCIA;

  function alternar(id: number) {
    const s = new Set(tildadas);
    if (s.has(id)) s.delete(id);
    else s.add(id);
    setTildadas(s);
  }

  return (
    <Tarjeta
      titulo="¿Qué trabajos cobra esta factura?"
      subtitulo="Marcá las órdenes de trabajo que incluye. El costo se reparte solo entre sus cultivos según la superficie."
      accion={
        <SoloLectura>
          <button
            type="button"
            onClick={() => guardar.mutate()}
            disabled={!cambio || guardar.isPending}
            className="rounded-md bg-finance px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {guardar.isPending ? "Guardando…" : cambio ? "Guardar órdenes" : "Sin cambios"}
          </button>
        </SoloLectura>
      }
    >
      <Comparacion haFactura={haFactura} fechaFactura={fechaFactura} haSel={haSel} cantidad={seleccionadas.length} />

      {data.ordenes.length === 0 ? (
        <p className="mt-3 text-sm text-ink-secondary">Este contratista no tiene órdenes de trabajo ejecutadas.</p>
      ) : (
        <>
          {probables.length > 0 ? (
            <>
              <p className="mt-4 text-xs font-medium uppercase tracking-wide text-ink-muted">
                Sin facturar, hasta {DIAS_PROBABLE} días antes de la factura
              </p>
              <ul className="mt-2 space-y-2">
                {probables.map((o) => (
                  <FilaOrden key={o.idOrden} o={o} tildada={tildadas.has(o.idOrden)} onClick={() => alternar(o.idOrden)}
                    fechaFactura={fechaFactura} coincide={coincide(o.hectareas)} />
                ))}
              </ul>
            </>
          ) : (
            <p className="mt-4 text-sm text-ink-secondary">No hay órdenes sin facturar en los {DIAS_PROBABLE} días previos a la factura.</p>
          )}
          {resto.length > 0 && (
            <div className="mt-3">
              <button type="button" onClick={() => setVerTodas(!verTodas)} className="text-sm text-finance hover:underline">
                {verTodas ? "Ocultar las demás órdenes" : `Ver las demás órdenes del contratista (${resto.length})`}
              </button>
              {verTodas && (
                <ul className="mt-2 max-h-80 space-y-2 overflow-y-auto pr-1">
                  {resto.map((o) => (
                    <FilaOrden key={o.idOrden} o={o} tildada={tildadas.has(o.idOrden)} onClick={() => alternar(o.idOrden)}
                      fechaFactura={fechaFactura} coincide={coincide(o.hectareas)} />
                  ))}
                </ul>
              )}
            </div>
          )}
        </>
      )}

      <Reparto filas={data.reparto} />
    </Tarjeta>
  );
}

function Tarjeta({ titulo, subtitulo, accion, children }: { titulo: string; subtitulo: string; accion?: React.ReactNode; children?: React.ReactNode }) {
  return (
    <section className="mt-3 rounded-lg border border-border bg-surface p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-ink-primary">{titulo}</h3>
          <p className="mt-0.5 text-sm text-ink-secondary">{subtitulo}</p>
        </div>
        {accion}
      </div>
      {children}
    </section>
  );
}

function Comparacion({ haFactura, fechaFactura, haSel, cantidad }: { haFactura: number | null; fechaFactura: string | null; haSel: number; cantidad: number }) {
  // Sergio 06/11: la orden lleva la superficie teórica de los lotes y la factura lo trabajado + repasos de cabeceras:
  // casi nunca coinciden. La diferencia es un dato para orientarse; solo una diferencia grande sugiere revisar.
  let estado: { texto: string; clase: string };
  if (cantidad === 0) estado = { texto: "Todavía no marcaste órdenes", clase: "bg-surface-sunken text-ink-secondary" };
  else if (haFactura == null) estado = { texto: "La factura no está en hectáreas: guiate por la fecha", clase: "bg-surface-sunken text-ink-secondary" };
  else {
    const dif = haSel - haFactura;
    const pct = formatNumero((Math.abs(dif) / haFactura) * 100, { max: 0 });
    const texto = `Diferencia ${dif >= 0 ? "+" : "−"}${ha(Math.abs(dif))} (${pct}%)`;
    estado = Math.abs(dif) / haFactura <= TOLERANCIA
      ? { texto: `${texto}: normal (superficie teórica vs. trabajada)`, clase: "bg-surface-sunken text-ink-secondary" }
      : { texto: `${texto}: revisá si falta o sobra alguna orden`, clase: "bg-status-warning-bg text-status-warning" };
  }
  return (
    <div className="mt-3 grid gap-2 sm:grid-cols-3">
      <Dato etiqueta="Factura" valor={haFactura != null ? ha(haFactura) : "—"} detalle={fechaFactura ? `del ${formatFecha(fechaFactura)}` : undefined} />
      <Dato etiqueta="Órdenes marcadas" valor={ha(haSel)} detalle={`${cantidad} ${cantidad === 1 ? "orden" : "órdenes"}`} />
      <div className={`flex items-center rounded-md px-3 py-2 text-sm font-medium ${estado.clase}`}>{estado.texto}</div>
    </div>
  );
}

function Dato({ etiqueta, valor, detalle }: { etiqueta: string; valor: string; detalle?: string }) {
  return (
    <div className="rounded-md bg-surface-sunken px-3 py-2">
      <div className="text-xs text-ink-muted">{etiqueta}</div>
      <div className="text-lg font-semibold tabular-nums text-ink-primary">
        {valor} {detalle && <span className="text-xs font-normal text-ink-secondary">{detalle}</span>}
      </div>
    </div>
  );
}

function FilaOrden({ o, tildada, onClick, fechaFactura, coincide }: {
  o: OrdenTrabajoDeCompra; tildada: boolean; onClick: () => void; fechaFactura: string | null; coincide: boolean;
}) {
  const dias = fechaFactura ? diasEntre(o.fecha, fechaFactura) : null;
  const cuando = dias == null ? "" : dias === 0 ? "el mismo día" : dias > 0 ? `${dias} días antes` : `${-dias} días después`;
  return (
    <li>
      <button
        type="button"
        onClick={onClick}
        aria-pressed={tildada}
        className={`flex w-full items-center gap-3 rounded-md border px-3 py-2.5 text-left transition ${
          tildada ? "border-finance bg-finance-light" : "border-border hover:border-finance/50 hover:bg-surface-sunken"
        }`}
      >
        <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded border text-xs ${tildada ? "border-finance bg-finance text-white" : "border-ink-muted"}`}>
          {tildada ? "✓" : ""}
        </span>
        <span className="w-28 shrink-0">
          <span className="block text-sm font-medium text-ink-primary">{formatFecha(o.fecha)}</span>
          <span className="block text-xs text-ink-secondary">{cuando}</span>
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm text-ink-primary">{o.labor ?? "Labor"}</span>
          <span className="block truncate text-xs text-ink-secondary" title={o.lotes ? `Lotes ${o.lotes}` : undefined}>
            {o.cultivos ?? "Sin cultivo"}
          </span>
        </span>
        <span className="flex shrink-0 flex-col items-end gap-1">
          <span className="text-sm font-semibold tabular-nums text-ink-primary">{ha(o.hectareas)}</span>
          {o.tieneOtraFactura && !o.vinculada ? (
            <span className="rounded-full bg-surface-sunken px-2 py-0.5 text-xs text-ink-secondary">Ya tiene factura</span>
          ) : coincide ? (
            <span className="rounded-full bg-status-success-bg px-2 py-0.5 text-xs text-status-success">Superficie parecida</span>
          ) : null}
        </span>
      </button>
    </li>
  );
}

function Reparto({ filas }: { filas: RepartoContratista[] }) {
  const porCultivo = useMemo(() => {
    const m = new Map<string, number>();
    for (const f of filas) {
      const k = `${f.cultivo ?? "Sin cultivo"} · ${f.campania ?? "sin campaña"}`;
      m.set(k, (m.get(k) ?? 0) + f.importe);
    }
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
  }, [filas]);
  if (porCultivo.length === 0) return null;
  const total = porCultivo.reduce((s, [, v]) => s + v, 0);
  return (
    <div className="mt-4 rounded-md bg-surface-sunken p-3">
      <p className="text-sm font-medium text-ink-primary">Así quedó imputado el costo</p>
      <ul className="mt-2 space-y-1.5">
        {porCultivo.map(([k, v]) => (
          <li key={k} className="text-sm">
            <div className="flex justify-between">
              <span>{k}</span>
              <span className="tabular-nums">{formatMoneda(v)}</span>
            </div>
            <div className="mt-0.5 h-1.5 rounded-full bg-border">
              <div className="h-1.5 rounded-full bg-finance" style={{ width: `${total ? Math.max(2, (v / total) * 100) : 0}%` }} />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
