"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";

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

/** 048: órdenes de trabajo que cobra esta factura del contratista. Franja de una línea (resumen de lo
 *  vinculado o aviso "Sin vincular"); las candidatas se abren a pedido en un desplegable que no empuja la grilla. */
export function OrdenesTrabajoPanel({ idCompra }: { idCompra: number }) {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const { data } = useQuery({ queryKey: ordenesTrabajoKey(idCompra), queryFn: () => fetchOrdenesTrabajoCompra(idCompra) });
  const [tildadas, setTildadas] = useState<Set<number>>(new Set());
  const [abierto, setAbierto] = useState(false);
  const cajaRef = useRef<HTMLDivElement | null>(null);
  const [verTodas, setVerTodas] = useState(false);

  useEffect(() => {
    if (data) setTildadas(new Set(data.ordenes.filter((o) => o.vinculada).map((o) => o.idOrden)));
  }, [data]);

  const guardar = useMutation({
    mutationFn: () => fijarOrdenesTrabajoCompra(idCompra, [...tildadas]),
    onSuccess: () => {
      showToast("Órdenes guardadas: el costo quedó imputado a sus cultivos.", "success");
      setAbierto(false);
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
      // Pedido o ejecución dentro de la ventana: una ejecución mal cargada (ej. marcada meses después, orden 150)
      // no debe esconder la orden.
      const enVentana = (f: string | null) => {
        if (!f) return false;
        const d = diasEntre(f, fechaFactura);
        return d >= 0 && d <= DIAS_PROBABLE;
      };
      return enVentana(o.fecha) || enVentana(o.fechaPedido);
    };
    return { probables: ordenes.filter(esProbable), resto: ordenes.filter((o) => !esProbable(o)) };
  }, [data, fechaFactura]);

  // Cierra el desplegable de candidatas al hacer clic afuera (sin perder lo tildado).
  useEffect(() => {
    if (!abierto) return;
    function fuera(e: MouseEvent) {
      if (cajaRef.current && !cajaRef.current.contains(e.target as Node)) setAbierto(false);
    }
    document.addEventListener("mousedown", fuera);
    return () => document.removeEventListener("mousedown", fuera);
  }, [abierto]);

  if (!data || !data.esContratista) return null;
  if (data.esNotaCreditoDebito) {
    return (
      <Franja titulo="Órdenes de trabajo">
        <span className="truncate text-ink-secondary">Se imputa igual que su factura (relacionala en Documentos relacionados).</span>
        <Reparto filas={data.reparto} />
      </Franja>
    );
  }
  if (!data.esDocumentoDeLabor) return null;

  const vinculadas = data.ordenes.filter((o) => o.vinculada);
  const seleccionadas = data.ordenes.filter((o) => tildadas.has(o.idOrden));
  const haSel = seleccionadas.reduce((s, o) => s + o.hectareas, 0);
  const cambio = data.ordenes.some((o) => o.vinculada !== tildadas.has(o.idOrden));
  const sinVincular = vinculadas.length === 0;

  function alternar(id: number) {
    const s = new Set(tildadas);
    if (s.has(id)) s.delete(id);
    else s.add(id);
    setTildadas(s);
  }

  function cancelar() {
    setAbierto(false);
    setTildadas(new Set(vinculadas.map((o) => o.idOrden)));
  }

  const resumen = sinVincular ? (
    data.ordenes.length === 0 ? (
      <span className="truncate text-ink-secondary">Sin órdenes pendientes de facturar para este contratista.</span>
    ) : (
      <span className="truncate text-status-warning">
        Sin vincular · {probables.length > 0 ? `${probables.length} probable${probables.length === 1 ? "" : "s"}` : `${data.ordenes.length} pendiente${data.ordenes.length === 1 ? "" : "s"}`}
      </span>
    )
  ) : (
    <span className="flex min-w-0 items-center gap-1 truncate" title={vinculadas.map((o) => `N° ${o.idOrden} · Pedido ${formatFecha(o.fechaPedido)} · ${o.labor ?? "Labor"} · ${ha(o.hectareas)}`).join("\n")}>
      {vinculadas.map((o, i) => (
        <span key={o.idOrden} className="shrink-0">
          {i > 0 && ", "}
          <LinkOrden idOrden={o.idOrden} />
        </span>
      ))}
      <span className="truncate">
        {vinculadas.length === 1
          ? ` · Orden del ${formatFecha(vinculadas[0].fechaPedido)} · ${vinculadas[0].labor ?? "Labor"} · ${ha(vinculadas[0].hectareas)}`
          : ` · ${vinculadas.length} órdenes · ${ha(vinculadas.reduce((s, o) => s + o.hectareas, 0))}`}
      </span>
    </span>
  );

  return (
    <div ref={cajaRef} className="relative">
      <Franja
        titulo="Órdenes de trabajo"
        accion={
          data.ordenes.length > 0 && (
            <SoloLectura>
              <button type="button" onClick={() => (abierto ? cancelar() : setAbierto(true))} className="whitespace-nowrap text-finance hover:underline">
                {abierto ? "Cerrar" : sinVincular ? "Elegir" : "Cambiar"}
              </button>
            </SoloLectura>
          )
        }
      >
        {resumen}
        {!sinVincular && <Diferencia haFactura={haFactura} haSel={haSel} />}
        {!sinVincular && <Reparto filas={data.reparto} />}
      </Franja>

      {abierto && (
        <div className="absolute left-0 right-0 top-full z-20 mt-1 rounded border border-border-strong bg-surface p-2 text-xs shadow-lg">
          <div className="mb-1 flex items-center justify-between gap-3">
            <span className="font-medium text-ink-primary">Órdenes que cobra esta factura</span>
            <span className="flex items-center gap-3">
              <Diferencia haFactura={haFactura} haSel={haSel} conFactura />
              <button type="button" onClick={cancelar} className="text-ink-secondary hover:underline">
                Cancelar
              </button>
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
          </div>
          <div className="max-h-64 overflow-y-auto rounded border border-border">
            {probables.length === 0 && (
              <div className="px-2 py-1 text-ink-secondary">Sin órdenes pedidas o ejecutadas en los {DIAS_PROBABLE} días previos a la factura.</div>
            )}
            {probables.map((o) => (
              <Fila key={o.idOrden} o={o} tildada={tildadas.has(o.idOrden)} onClick={() => alternar(o.idOrden)} fechaFactura={fechaFactura} haFactura={haFactura} />
            ))}
            {resto.length > 0 && !verTodas && (
              <button type="button" onClick={() => setVerTodas(true)} className="w-full px-2 py-1 text-left text-finance hover:underline">
                Ver otras órdenes del contratista ({resto.length})
              </button>
            )}
            {verTodas &&
              resto.map((o) => (
                <Fila key={o.idOrden} o={o} tildada={tildadas.has(o.idOrden)} onClick={() => alternar(o.idOrden)} fechaFactura={fechaFactura} haFactura={haFactura} />
              ))}
          </div>
        </div>
      )}
    </div>
  );
}

/** N° de orden que abre la orden completa en otra pestaña (no tilda la fila). */
function LinkOrden({ idOrden, className = "" }: { idOrden: number; className?: string }) {
  return (
    <a
      href={`/produccion/ordenes/${idOrden}`}
      target="_blank"
      rel="noopener noreferrer"
      onClick={(e) => e.stopPropagation()}
      title="Abrir la orden en otra pestaña"
      className={`tabular-nums text-finance underline hover:opacity-80 ${className}`}
    >
      N° {idOrden}
    </a>
  );
}

/** Franja de una línea: título, resumen (se trunca) y acción a la derecha. */
function Franja({ titulo, accion, children }: { titulo: string; accion?: React.ReactNode; children?: React.ReactNode }) {
  return (
    <section className="flex h-7 items-center gap-2 rounded border border-border bg-surface px-2 text-xs">
      <span className="shrink-0 font-medium text-ink-secondary">{titulo}:</span>
      <div className="flex min-w-0 flex-1 items-center gap-2 overflow-hidden whitespace-nowrap">{children}</div>
      {accion}
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
      <LinkOrden idOrden={o.idOrden} className="w-14 shrink-0" />
      {/* Pedido = la fecha del listado de órdenes; ejecutada = la que se compara con la factura. */}
      <span className="w-28 shrink-0 tabular-nums">Pedido {formatFecha(o.fechaPedido)}</span>
      <span className="w-48 shrink-0 tabular-nums text-ink-secondary">
        Ejecutada {formatFecha(o.fecha)}
        {dias == null ? "" : dias >= 0 ? ` (${dias} d antes)` : ` (${-dias} d después)`}
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
    <span className="min-w-0 truncate text-ink-secondary" title={porCultivo.map(([k, v]) => `${k} ${formatMoneda(v)}`).join("\n")}>
      · Imputado a {porCultivo.map(([k, v]) => `${k} ${formatMoneda(v)}`).join(" · ")}
    </span>
  );
}
