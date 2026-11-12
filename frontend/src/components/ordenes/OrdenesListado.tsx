"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { CultivoChip } from "@/components/cultivos/CultivoChip";
import { SideDrawer } from "@/components/ui/SideDrawer";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { BadgeEstadoOrden } from "@/components/ordenes/EstadosOrden";
import { formatCantidad, formatFecha, formatNumero } from "@/lib/format";
import { fetchCatalogosOrdenes, fetchOrden, fetchOrdenes, type FiltrosOrdenes, type OrdenListItem } from "@/services/ordenesApi";

const ESTADOS = [
  { value: "", label: "Todas" },
  { value: "Planificada", label: "Planificadas" },
  { value: "Ejecutada", label: "Ejecutadas" },
  { value: "Anulada", label: "Anuladas" },
];

const VACIO: FiltrosOrdenes = { fechaDesde: "", fechaHasta: "", estado: "", insumo: "" };
const POR_PAGINA = 50;
const CTRL = "h-8 rounded border border-border bg-surface px-2 text-sm";

/** Listado compacto (12/11/2026): barra única de filtros, tabla densa con títulos fijos y detalle rápido en panel lateral. */
export function OrdenesListado() {
  const [filtros, setFiltros] = useState<FiltrosOrdenes>(VACIO);
  // El texto del insumo se aplica al tocar Enter o salir del campo, no en cada tecla.
  const [insumo, setInsumo] = useState("");
  const [page, setPage] = useState(1);
  const [abierta, setAbierta] = useState<number | null>(null);
  const { data, isLoading, isError } = useQuery({
    queryKey: ["ordenes", filtros, page],
    queryFn: () => fetchOrdenes(filtros, page, POR_PAGINA),
  });
  const { data: catalogos } = useQuery({ queryKey: ["ordenes-catalogos"], queryFn: fetchCatalogosOrdenes, staleTime: 300_000 });
  const cambiar = (f: Partial<FiltrosOrdenes>) => {
    setPage(1);
    setFiltros({ ...filtros, ...f });
  };
  const aplicarInsumo = () => insumo.trim() !== (filtros.insumo ?? "") && cambiar({ insumo: insumo.trim() });
  const hayFiltros = JSON.stringify(filtros) !== JSON.stringify(VACIO) || insumo !== "";
  const campanias = [...(catalogos?.campanias ?? [])].sort((a, b) => b.nombre.localeCompare(a.nombre));
  const ultimas = campanias.filter((c) => /^\d{4}/.test(c.nombre)).slice(0, 4);
  const conInsumo = !!filtros.insumo;
  const totalPaginas = data ? Math.max(1, Math.ceil(data.total / data.pageSize)) : 1;
  const haPagina = (data?.items ?? []).reduce((s, o) => s + (o.estado === "Anulada" ? 0 : o.hectareas || 0), 0);

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2">
      {/* Filtros rápidos: estado y últimas campañas */}
      <div className="flex flex-wrap items-center gap-1.5 text-sm">
        {ESTADOS.map((e) => (
          <button key={e.value} type="button" onClick={() => cambiar({ estado: e.value })}
            className={`rounded-full border px-2.5 py-0.5 ${filtros.estado === e.value ? "border-finance bg-finance text-white" : "border-border hover:bg-surface-sunken"}`}>
            {e.label}
          </button>
        ))}
        {ultimas.length > 0 && <span className="mx-1 h-4 w-px bg-border" aria-hidden />}
        {ultimas.map((c) => (
          <button key={c.idCampania} type="button" onClick={() => cambiar({ idCampania: filtros.idCampania === c.idCampania ? null : c.idCampania })}
            className={`rounded-full border px-2.5 py-0.5 ${filtros.idCampania === c.idCampania ? "border-finance bg-finance text-white" : "border-border hover:bg-surface-sunken"}`}>
            {c.nombre}
          </button>
        ))}
      </div>

      {/* Barra única de filtros */}
      <div className="flex flex-wrap items-center gap-2">
        <input className={`${CTRL} w-56`} placeholder="Buscar insumo o principio activo" value={insumo}
          onChange={(e) => setInsumo(e.target.value)} onBlur={aplicarInsumo} onKeyDown={(e) => e.key === "Enter" && aplicarInsumo()} />
        <select className={CTRL} value={filtros.idCampania ?? ""} onChange={(e) => cambiar({ idCampania: e.target.value ? Number(e.target.value) : null })} aria-label="Campaña">
          <option value="">Campaña: todas</option>
          {campanias.map((c) => <option key={c.idCampania} value={c.idCampania}>{c.nombre}</option>)}
        </select>
        <select className={CTRL} value={filtros.idCultivo ?? ""} onChange={(e) => cambiar({ idCultivo: e.target.value ? Number(e.target.value) : null })} aria-label="Cultivo">
          <option value="">Cultivo: todos</option>
          {(catalogos?.cultivos ?? []).map((c) => <option key={c.idCultivo} value={c.idCultivo}>{c.nombre}</option>)}
        </select>
        <select className={CTRL} value={filtros.idTipoLabor ?? ""} onChange={(e) => cambiar({ idTipoLabor: e.target.value ? Number(e.target.value) : null })} aria-label="Labor">
          <option value="">Labor: todas</option>
          {(catalogos?.tiposLabor ?? []).map((t) => <option key={t.idTipoLabor} value={t.idTipoLabor}>{t.nombre}</option>)}
        </select>
        <select className={`${CTRL} max-w-[14rem]`} value={filtros.idContratista ?? ""} onChange={(e) => cambiar({ idContratista: e.target.value ? Number(e.target.value) : null })} aria-label="Contratista">
          <option value="">Contratista: todos</option>
          {(catalogos?.contratistas ?? []).map((c) => <option key={c.idContratistaContacto} value={c.idContratistaContacto}>{c.nombre}</option>)}
        </select>
        <input type="date" className={CTRL} value={filtros.fechaDesde} onChange={(e) => cambiar({ fechaDesde: e.target.value })} title="Desde" aria-label="Desde" />
        <span className="text-ink-muted">–</span>
        <input type="date" className={CTRL} value={filtros.fechaHasta} onChange={(e) => cambiar({ fechaHasta: e.target.value })} title="Hasta" aria-label="Hasta" />
        {hayFiltros && (
          <button type="button" onClick={() => { setInsumo(""); setPage(1); setFiltros(VACIO); }} className="text-sm text-finance hover:underline">
            Limpiar
          </button>
        )}
      </div>

      {isLoading && <LoadingState />}
      {isError && <ErrorState message="No se pudieron cargar las órdenes." />}
      {data && (
        <>
          <div className="min-h-0 flex-1 overflow-auto rounded border border-border" style={{ maxHeight: "calc(100vh - 13rem)" }}>
            <table className="w-full text-sm">
              <thead className="sticky top-0 z-10 bg-surface-sunken text-left text-xs text-ink-secondary">
                <tr>
                  <th className="px-2 py-1.5 font-medium">Fecha</th>
                  <th className="px-2 py-1.5 text-right font-medium">N°</th>
                  <th className="px-2 py-1.5 font-medium">Labor</th>
                  <th className="px-2 py-1.5 font-medium">Contratista</th>
                  <th className="px-2 py-1.5 font-medium">Cultivo / campaña</th>
                  <th className="px-2 py-1.5 font-medium">Lotes</th>
                  <th className="px-2 py-1.5 text-right font-medium">Ha</th>
                  {conInsumo && <th className="px-2 py-1.5 font-medium">Insumo usado</th>}
                  <th className="px-2 py-1.5 font-medium">Estado</th>
                  <th className="px-2 py-1.5" />
                </tr>
              </thead>
              <tbody>
                {data.items.length === 0 && (
                  <tr><td colSpan={10} className="px-2 py-6 text-center text-ink-secondary">No hay órdenes de trabajo con estos filtros.</td></tr>
                )}
                {data.items.map((o) => (
                  <Fila key={o.idOrden} o={o} conInsumo={conInsumo} activa={abierta === o.idOrden} onClick={() => setAbierta(o.idOrden)} />
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between text-xs text-ink-secondary">
            <span className="font-data">
              {formatNumero(data.total, { max: 0 })} órdenes · {formatNumero(haPagina, { max: 1 })} ha en esta página (sin anuladas)
            </span>
            {totalPaginas > 1 && (
              <span className="flex items-center gap-2">
                <button type="button" disabled={page <= 1} onClick={() => setPage(page - 1)} className="rounded border border-border px-2 py-0.5 disabled:opacity-40">‹</button>
                <span className="font-data">{page} / {totalPaginas}</span>
                <button type="button" disabled={page >= totalPaginas} onClick={() => setPage(page + 1)} className="rounded border border-border px-2 py-0.5 disabled:opacity-40">›</button>
              </span>
            )}
          </div>
        </>
      )}

      <SideDrawer open={abierta != null} onClose={() => setAbierta(null)} title={abierta != null ? `Orden N° ${abierta}` : ""} maxWidthClass="max-w-xl">
        {abierta != null && <DetalleRapido idOrden={abierta} />}
      </SideDrawer>
    </div>
  );
}

function Fila({ o, conInsumo, activa, onClick }: { o: OrdenListItem; conInsumo: boolean; activa: boolean; onClick: () => void }) {
  return (
    <tr onClick={onClick}
      className={`cursor-pointer border-t border-border hover:bg-surface-sunken ${activa ? "bg-finance/10" : ""} ${o.estado === "Anulada" ? "text-ink-muted line-through decoration-ink-muted/40" : ""}`}>
      <td className="whitespace-nowrap px-2 py-1 font-data">{formatFecha(o.fechaPedido)}</td>
      <td className="px-2 py-1 text-right font-data">{o.idOrden}</td>
      <td className="whitespace-nowrap px-2 py-1">{o.tipoLabor ?? "—"}</td>
      <td className="max-w-[18rem] truncate px-2 py-1" title={o.contratista ?? "Maquinaria propia"}>
        {o.contratista ?? <span className="text-ink-secondary">Maquinaria propia</span>}
      </td>
      <td className="px-2 py-1">
        <div className="flex flex-wrap gap-1">
          {(o.cultivos ?? []).map((c) => (
            <span key={`${c.cultivo}|${c.campania}`} className="inline-flex items-center gap-1">
              <CultivoChip cultivo={c.cultivo} /><span className="text-xs text-ink-secondary">{c.campania}</span>
            </span>
          ))}
          {!o.cultivos?.length && <span className="text-ink-muted">—</span>}
        </div>
      </td>
      <td className="max-w-[12rem] truncate px-2 py-1 text-xs" title={(o.lotes ?? []).join(", ")}>{(o.lotes ?? []).join(", ") || "—"}</td>
      <td className="whitespace-nowrap px-2 py-1 text-right font-data">{o.hectareas ? formatNumero(o.hectareas, { max: 1 }) : "—"}</td>
      {conInsumo && (
        <td className="px-2 py-1 text-xs">
          {(o.insumosCoincidentes ?? []).map((i) => (
            <span key={i.producto} className="block whitespace-nowrap">
              {i.producto}: <span className="font-data">{formatCantidad(i.cantidad)}</span> {i.unidad}
            </span>
          ))}
        </td>
      )}
      <td className="px-2 py-1 no-underline"><BadgeEstadoOrden estado={o.estado} /></td>
      <td className="px-2 py-1 text-right">
        <Link href={`/produccion/ordenes/${o.idOrden}`} onClick={(e) => e.stopPropagation()} className="text-xs text-finance hover:underline">
          Abrir
        </Link>
      </td>
    </tr>
  );
}

/** Resumen de la orden en el panel lateral: lotes con su cultivo/campaña e insumos. */
function DetalleRapido({ idOrden }: { idOrden: number }) {
  const { data: o, isLoading, isError } = useQuery({ queryKey: ["orden", idOrden], queryFn: () => fetchOrden(idOrden) });
  if (isLoading) return <LoadingState />;
  if (isError || !o) return <ErrorState message="No se pudo cargar la orden." />;
  // Lotes únicos (cada lote una vez, con su cultivo y campaña).
  const lotes = new Map<string, { lote: string; cultivo: string | null; campania: string | null; superficie: number }>();
  o.insumos.forEach((r) => r.distribuciones.forEach((d) => {
    const k = `${d.lote}|${d.cultivo}|${d.campania}`;
    if (!lotes.has(k)) lotes.set(k, { lote: d.lote ?? "—", cultivo: d.cultivo, campania: d.campania, superficie: d.superficie });
  }));
  return (
    <div className="space-y-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <BadgeEstadoOrden estado={o.estado} />
        <span className="font-medium">{o.tipoLabor ?? "—"}</span>
        <span className="text-ink-secondary">· {o.contratista ?? "Maquinaria propia"}</span>
      </div>
      <dl className="grid grid-cols-3 gap-2">
        <div><dt className="text-xs text-ink-secondary">Pedido</dt><dd className="font-data">{formatFecha(o.fechaPedido)}</dd></div>
        <div><dt className="text-xs text-ink-secondary">Ejecución</dt><dd className="font-data">{formatFecha(o.fechaEjecucion)}</dd></div>
        <div><dt className="text-xs text-ink-secondary">Superficie</dt><dd className="font-data">{formatNumero(o.hectareas, { max: 1 })} ha</dd></div>
      </dl>
      {lotes.size > 0 && (
        <table className="w-full">
          <thead className="text-left text-xs text-ink-secondary"><tr><th className="py-1">Lote</th><th>Cultivo</th><th>Campaña</th><th className="text-right">Ha</th></tr></thead>
          <tbody>
            {[...lotes.values()].map((l) => (
              <tr key={`${l.lote}|${l.cultivo}|${l.campania}`} className="border-t border-border">
                <td className="py-1">{l.lote}</td>
                <td><CultivoChip cultivo={l.cultivo} /></td>
                <td>{l.campania ?? "—"}</td>
                <td className="text-right font-data">{formatNumero(l.superficie, { max: 1 })}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {o.insumos.length > 0 && (
        <div>
          <div className="mb-1 text-xs text-ink-secondary">Insumos</div>
          <ul className="space-y-0.5">
            {o.insumos.map((r) => (
              <li key={r.idOrdenInsumo} className="flex justify-between gap-3">
                <span className="truncate">{r.producto ?? "—"}</span>
                <span className="whitespace-nowrap font-data">{formatCantidad(r.cantidadTotal + r.ajusteRecuento)} {r.unidad}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {o.observaciones && <p className="rounded bg-surface-sunken p-2 text-xs">{o.observaciones}</p>}
      <div className="flex gap-2 pt-1">
        <Link href={`/produccion/ordenes/${o.idOrden}`} className="rounded bg-finance px-3 py-1.5 text-white">Ver orden completa</Link>
        {o.editable && <Link href={`/produccion/ordenes/${o.idOrden}/editar`} className="rounded border border-border px-3 py-1.5 hover:bg-surface-sunken">Editar</Link>}
      </div>
    </div>
  );
}
