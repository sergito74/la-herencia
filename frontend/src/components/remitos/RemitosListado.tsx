"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { fetchRemitos, urlExportarRemitos, type FiltrosRemitos, type RemitoListItem } from "@/services/remitosApi";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { FilterBar, FilterField, FilterSubmitButton, filterInputClass } from "@/components/ui/FilterBar";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { BadgeFactura, BadgeRenglones, BotonExcel } from "@/components/remitos/EstadosRemito";

const ESTADOS = [
  { value: "", label: "Todos" },
  { value: "sinFactura", label: "Sin factura" },
  { value: "sinVincular", label: "Renglones sin vincular" },
  { value: "parcial", label: "Vinculación parcial" },
  { value: "completo", label: "Vinculación completa" },
  { value: "conDiferencia", label: "Con diferencia" },
  { value: "revisar", label: "Duplicados a revisar" },
  { value: "anulado", label: "Anulados" },
];

interface Form {
  idProveedor: number | null;
  proveedor: string | null;
  producto: string;
  nroRemito: string;
  fechaDesde: string;
  fechaHasta: string;
  estado: string;
}

const VACIO: Form = { idProveedor: null, proveedor: null, producto: "", nroRemito: "", fechaDesde: "", fechaHasta: "", estado: "" };

const COLUMNAS: DataTableColumn<RemitoListItem>[] = [
  {
    key: "fecha",
    header: "Fecha",
    numeric: true,
    render: (r) => (
      <Link className="whitespace-nowrap text-finance underline" href={`/produccion/remitos/${r.idRemito}`}>
        {r.fecha ?? "—"}
      </Link>
    ),
  },
  { key: "proveedor", header: "Proveedor", render: (r) => r.proveedor ?? "—" },
  {
    key: "nro",
    header: "N° de remito",
    render: (r) => (
      <span className="whitespace-nowrap">
        {r.nroRemito ?? "—"}
        {r.revisarDuplicado && (
          <span className="ml-1">
            <StatusBadge label="Duplicado" tone="warning" />
          </span>
        )}
        {r.anulado && (
          <span className="ml-1">
            <StatusBadge label="Anulado" tone="danger" />
          </span>
        )}
      </span>
    ),
  },
  { key: "productos", header: "Productos", render: (r) => <span className="text-xs">{r.productos || "—"}</span> },
  {
    key: "factura",
    header: "Factura",
    render: (r) => (
      <div className="space-y-0.5">
        <BadgeFactura estado={r.estadoFactura} dias={r.diasSinFactura} />
        {r.facturas.length > 0 && <div className="text-xs text-ink-secondary">{r.facturas.join(", ")}</div>}
      </div>
    ),
  },
  { key: "renglones", header: "Renglones", render: (r) => <BadgeRenglones estado={r.estadoRenglones} /> },
];

/** Listado de remitos (010): por proveedor y fecha, con filtros por producto y estado. */
export function RemitosListado() {
  const [form, setForm] = useState<Form>(VACIO);
  const [aplicados, setAplicados] = useState<Form>(VACIO);
  const [page, setPage] = useState(1);

  const filtros: FiltrosRemitos = {
    idProveedor: aplicados.idProveedor,
    producto: aplicados.producto || undefined,
    nroRemito: aplicados.nroRemito || undefined,
    fechaDesde: aplicados.fechaDesde || undefined,
    fechaHasta: aplicados.fechaHasta || undefined,
    estado: aplicados.estado || undefined,
  };
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["remitos", filtros, page],
    queryFn: () => fetchRemitos(filtros, page),
    staleTime: 0,
  });

  function aplicar(nuevo: Form) {
    setForm(nuevo);
    setAplicados(nuevo);
    setPage(1);
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap gap-1">
          {ESTADOS.map((e) => (
            <button
              key={e.value}
              type="button"
              onClick={() => aplicar({ ...form, estado: e.value })}
              className={`rounded-full border px-3 py-1 text-xs ${
                aplicados.estado === e.value ? "border-finance bg-finance text-white" : "border-border text-ink-secondary hover:bg-surface-sunken"
              }`}
            >
              {e.label}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          <BotonExcel href={urlExportarRemitos(filtros)} />
          <Link href="/produccion/remitos/nuevo" className="rounded-sm bg-finance px-4 py-2 text-sm text-white hover:opacity-90">
            + Nuevo remito
          </Link>
        </div>
      </div>

      <FilterBar
        onSubmit={(e) => {
          e.preventDefault();
          aplicar(form);
        }}
      >
        <FilterField label="Proveedor">
          <ContactoSelect
            value={form.idProveedor}
            razonSocial={form.proveedor}
            tipoContacto={["Proveedor", "Multiple"]}
            onChange={(id, nombre) => setForm({ ...form, idProveedor: id, proveedor: nombre })}
            placeholder="Todos"
          />
        </FilterField>
        <FilterField label="Producto">
          <input className={filterInputClass} value={form.producto} onChange={(e) => setForm({ ...form, producto: e.target.value })} placeholder="Nombre o principio activo…" />
        </FilterField>
        <FilterField label="N° de remito">
          <input className={filterInputClass} value={form.nroRemito} onChange={(e) => setForm({ ...form, nroRemito: e.target.value })} />
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
      {isError && <ErrorState message="No se pudieron cargar los remitos." onRetry={() => refetch()} />}
      {data && (
        <DataTable
          columns={COLUMNAS}
          rows={data.items}
          keyField={(r) => r.idRemito}
          emptyMessage="No hay remitos con estos filtros."
          page={data.page}
          pageSize={data.pageSize}
          total={data.total}
          onPageChange={setPage}
        />
      )}
    </div>
  );
}
