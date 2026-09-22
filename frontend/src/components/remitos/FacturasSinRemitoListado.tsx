"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { fetchFacturasSinRemito, type FacturaSinRemito } from "@/services/remitosApi";
import { formatMoneda } from "@/lib/format";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { FilterBar, FilterField, FilterSubmitButton, filterInputClass } from "@/components/ui/FilterBar";
import { ErrorState, LoadingState } from "@/components/ui/States";

const haceUnAnio = () => {
  const d = new Date();
  d.setFullYear(d.getFullYear() - 1);
  return d.toISOString().slice(0, 10);
};

/** Facturas de insumos que no tienen remito vinculado (una factura puede llegar sin remito). */
export function FacturasSinRemitoListado() {
  const inicial = { proveedor: "", fechaDesde: haceUnAnio(), fechaHasta: "" };
  const [form, setForm] = useState(inicial);
  const [aplicados, setAplicados] = useState(inicial);
  const [page, setPage] = useState(1);
  const filtros = { proveedor: aplicados.proveedor || undefined, fechaDesde: aplicados.fechaDesde || undefined, fechaHasta: aplicados.fechaHasta || undefined };
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["facturas-sin-remito", filtros, page], queryFn: () => fetchFacturasSinRemito(filtros, page), staleTime: 0 });

  const columnas: DataTableColumn<FacturaSinRemito>[] = [
    { key: "fecha", header: "Fecha", numeric: true, render: (f) => f.fecha ?? "—" },
    { key: "proveedor", header: "Proveedor", render: (f) => f.proveedor },
    {
      key: "doc",
      header: "Factura",
      render: (f) => (
        <Link className="text-finance underline" href={`/compras/${f.idCompra}`}>
          {f.tipoDocumento} {f.numeroDocumento}
        </Link>
      ),
    },
    { key: "renglones", header: "Renglones de insumos", numeric: true, align: "right", render: (f) => f.renglones },
    { key: "neto", header: "Neto", numeric: true, align: "right", render: (f) => formatMoneda(f.neto, f.moneda === "Dolares" ? "Dolares" : "Pesos") },
    {
      key: "acc",
      header: "",
      render: (f) => (
        <Link className="text-xs text-finance underline" href={`/produccion/remitos/nuevo?idProveedor=${f.idProveedor}&proveedor=${encodeURIComponent(f.proveedor ?? "")}`}>
          Cargar remito
        </Link>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <p className="text-sm text-ink-secondary">
        Facturas con renglones de insumos que todavía no tienen remito. Puede ser normal (el proveedor entrega y factura por separado): sirve para detectar mercadería que llegó y no se cargó.
      </p>
      <FilterBar
        onSubmit={(e) => {
          e.preventDefault();
          setAplicados(form);
          setPage(1);
        }}
      >
        <FilterField label="Proveedor">
          <input className={filterInputClass} value={form.proveedor} onChange={(e) => setForm({ ...form, proveedor: e.target.value })} placeholder="Razón social…" />
        </FilterField>
        <FilterField label="Desde">
          <input type="date" className={filterInputClass} value={form.fechaDesde} onChange={(e) => setForm({ ...form, fechaDesde: e.target.value })} />
        </FilterField>
        <FilterField label="Hasta">
          <input type="date" className={filterInputClass} value={form.fechaHasta} onChange={(e) => setForm({ ...form, fechaHasta: e.target.value })} />
        </FilterField>
        <FilterSubmitButton />
      </FilterBar>
      {isLoading && <LoadingState />}
      {isError && <ErrorState message="No se pudieron cargar las facturas." onRetry={() => refetch()} />}
      {data && <DataTable columns={columnas} rows={data.items} keyField={(f) => f.idCompra} emptyMessage="No hay facturas de insumos sin remito en este período." page={data.page} pageSize={data.pageSize} total={data.total} onPageChange={setPage} />}
    </div>
  );
}
