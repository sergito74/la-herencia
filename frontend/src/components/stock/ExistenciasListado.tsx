"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { fetchExistencias, fetchKardex, fetchTiposProducto, urlExportarExistencias, urlRecuentoFisico, type Existencia } from "@/services/remitosApi";
import { formatCantidad, formatMoneda, formatFecha } from "@/lib/format";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { filterInputClass } from "@/components/ui/FilterBar";
import { TiraIndicadores } from "@/components/ui/TiraIndicadores";
import { SideDrawer } from "@/components/ui/SideDrawer";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { BotonExcel } from "@/components/remitos/EstadosRemito";

const ESTADOS = [
  { value: "conStock", label: "Con stock" },
  { value: "costoPendiente", label: "Con costo pendiente" },
  { value: "negativo", label: "Stock negativo" },
  { value: "todos", label: "Todos" },
];

function Kardex({ idProducto, onClose }: { idProducto: number | null; onClose: () => void }) {
  const { data, isLoading } = useQuery({
    queryKey: ["kardex", idProducto],
    queryFn: () => fetchKardex(idProducto!),
    enabled: idProducto != null,
    staleTime: 0,
  });
  return (
    <SideDrawer open={idProducto != null} onClose={onClose} title={data ? `Kardex — ${data.producto.producto}` : "Kardex"} maxWidthClass="max-w-4xl">
      {isLoading && <LoadingState />}
      {data && (
        <div className="space-y-3">
          <p className="text-xs text-ink-secondary">
            Existencia {formatCantidad(data.existencia)} {data.unidadBase} · valor a costo FIFO {formatMoneda(data.valor)}. Las salidas toman el costo de las entradas más
            antiguas; las marcadas «costo pendiente» se recalculan solas al vincular la factura.
          </p>
          <table className="w-full text-xs">
            <thead className="sticky top-[53px] z-10 text-left text-ink-secondary bg-surface">
              <tr>
                <th className="py-1 pr-2">Fecha</th>
                <th className="pr-2">Movimiento</th>
                <th className="pr-2 text-right">Cantidad</th>
                <th className="pr-2 text-right">Costo unit.</th>
                <th className="pr-2 text-right">Importe</th>
                <th className="text-right">Saldo</th>
              </tr>
            </thead>
            <tbody>
              {data.movimientos.map((m) => (
                <tr key={m.clave} className="border-t border-border">
                  <td className="py-1 pr-2 whitespace-nowrap">{formatFecha(m.fecha)}</td>
                  <td className="pr-2">
                    <span className={m.cantidad >= 0 ? "text-status-success" : "text-ink-primary"}>{m.tipo}</span> · {m.detalle}
                    {m.costoPendiente && <span className="ml-1"><StatusBadge label="Costo pendiente" tone="warning" /></span>}
                    {!!m.sinCobertura && <span className="ml-1"><StatusBadge label={`Sin cobertura ${formatCantidad(m.sinCobertura)}`} tone="danger" /></span>}
                  </td>
                  <td className={`pr-2 text-right font-data ${m.cantidad < 0 ? "text-status-danger" : ""}`}>{formatCantidad(m.cantidad)}</td>
                  <td className="pr-2 text-right font-data">{m.costoUnitario != null ? formatMoneda(m.costoUnitario) : "—"}</td>
                  <td className="pr-2 text-right font-data">{m.importe != null ? formatMoneda(m.importe) : "—"}</td>
                  <td className="text-right font-data font-medium">{formatCantidad(m.saldo)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </SideDrawer>
  );
}

/** Existencias de insumos valorizadas por FIFO (010). */
export function ExistenciasListado() {
  const [form, setForm] = useState({ q: "", tipo: "", estado: "conStock" });
  const [aplicados, setAplicados] = useState(form);
  const [kardex, setKardex] = useState<number | null>(null);
  const { data: tipos } = useQuery({ queryKey: ["tipos-producto"], queryFn: fetchTiposProducto, staleTime: Infinity });
  const filtros = { q: aplicados.q || undefined, tipo: aplicados.tipo || undefined, estado: aplicados.estado };
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["existencias", filtros], queryFn: () => fetchExistencias(filtros), staleTime: 0 });

  const columnas: DataTableColumn<Existencia>[] = [
    {
      key: "producto",
      header: "Producto",
      render: (r) => (
        <button type="button" className="text-left text-finance underline" onClick={() => setKardex(r.idProducto)}>
          {r.producto}
        </button>
      ),
    },
    { key: "ingredienteActivo", header: "Principio activo", render: (r) => r.ingredienteActivo ?? "—" },
    { key: "tipo", header: "Tipo", render: (r) => r.tipo ?? "—" },
    { key: "unidad", header: "Unidad", render: (r) => r.unidadBase ?? "—" },
    { key: "existencia", header: "Existencia", numeric: true, align: "right", render: (r) => <span className={r.negativo ? "text-status-danger" : ""}>{formatCantidad(r.existencia)}</span> },
    { key: "valor", header: "Valor (FIFO)", numeric: true, align: "right", render: (r) => formatMoneda(r.valor) },
    { key: "costo", header: "Costo promedio", numeric: true, align: "right", render: (r) => (r.costoPromedio != null ? formatMoneda(r.costoPromedio) : "—") },
    {
      key: "obs",
      header: "",
      render: (r) => (
        <span className="flex flex-wrap gap-1">
          {r.cantidadCostoPendiente > 0.005 && <StatusBadge label={`Sin costo: ${formatCantidad(r.cantidadCostoPendiente)}`} tone="warning" />}
          {r.negativo && <StatusBadge label="Negativo" tone="danger" />}
          {r.equivalenciaPendiente && <StatusBadge label="Falta equivalencia" tone="warning" />}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-2">
      {/* 19/11/2026 (anatomía de hoja): indicadores, filtros y acciones en una fila. */}
      <div className="flex flex-wrap items-center gap-2">
        {data && (
          <TiraIndicadores compacta items={[
            { titulo: "Productos", valor: formatCantidad(data.totales.productos) },
            { titulo: "Valor (FIFO)", valor: formatMoneda(data.totales.valor) },
            { titulo: "Costo pendiente", valor: formatCantidad(data.totales.conCostoPendiente), aviso: !!data.totales.conCostoPendiente },
            { titulo: "Negativos", valor: formatCantidad(data.totales.negativos), aviso: !!data.totales.negativos },
          ]} />
        )}
        <form className="flex flex-wrap items-center gap-2" onSubmit={(e) => { e.preventDefault(); setAplicados(form); }}>
          <input className={`${filterInputClass} w-48`} aria-label="Producto" value={form.q} onChange={(e) => setForm({ ...form, q: e.target.value })} placeholder="Buscar producto…" />
          <select className={filterInputClass} aria-label="Tipo" value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>
            <option value="">Todos los tipos</option>
            {tipos?.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <select className={filterInputClass} aria-label="Mostrar" value={form.estado} onChange={(e) => setForm({ ...form, estado: e.target.value })}>
            {ESTADOS.map((e) => <option key={e.value} value={e.value}>{e.label}</option>)}
          </select>
          <button type="submit" className="h-8 rounded-sm bg-finance px-3 text-sm font-medium text-white hover:bg-finance/90">Buscar</button>
        </form>
        <div className="ml-auto flex gap-2">
          <a href={urlRecuentoFisico(filtros)} title="Planilla imprimible para contar el stock en el campo, con los filtros aplicados."
            className="h-8 rounded-sm border border-finance px-3 py-1.5 text-sm text-finance hover:bg-finance-light">Planilla de recuento</a>
          <BotonExcel href={urlExportarExistencias(filtros)} />
        </div>
      </div>
      {isLoading && <LoadingState />}
      {isError && <ErrorState message="No se pudieron cargar las existencias." onRetry={() => refetch()} />}
      {data && (
        <DataTable columns={columnas} rows={data.items} keyField={(r) => r.idProducto} emptyMessage="No hay productos con estos filtros." page={1} pageSize={Math.max(data.items.length, 1)} total={data.items.length} onPageChange={() => undefined} />
      )}
      <Kardex idProducto={kardex} onClose={() => setKardex(null)} />
    </div>
  );
}
