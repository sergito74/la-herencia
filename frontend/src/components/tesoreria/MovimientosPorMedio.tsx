"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import {
  fetchMovimientos,
  type Medio,
  type MovimientoPorMedio,
} from "@/services/tesoreriaApi";
import { ReferenciaOrigen } from "@/components/tesoreria/ReferenciaOrigen";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { FilterBar, FilterField, filterInputClass } from "@/components/ui/FilterBar";
import { ErrorState, LoadingState } from "@/components/ui/States";

const MEDIO_LABELS: Record<Medio, string> = {
  bna: "Banco Nación",
  galicia: "Galicia",
  efectivo: "Pagos en efectivo",
  "valores-propios": "Valores propios",
  "valores-recibidos": "Valores recibidos",
  tarjetas: "Tarjetas",
};

interface ColumnDef {
  key: string;
  header: string;
  numeric?: boolean;
  render: (item: any) => React.ReactNode;
}

function columnsFor(medio: Medio): ColumnDef[] {
  switch (medio) {
    case "bna":
      return [
        { key: "fechaHora", header: "Fecha/Hora", numeric: true, render: (m: any) => m.fechaHora ?? "—" },
        { key: "concepto", header: "Concepto", render: (m: any) => m.concepto ?? "—" },
        { key: "importe", header: "Importe", numeric: true, render: (m: any) => m.importe ?? "—" },
        { key: "contacto", header: "Contacto", render: (m: any) => m.contacto ?? "—" },
      ];
    case "galicia":
      return [
        { key: "fecha", header: "Fecha", numeric: true, render: (m: any) => m.fecha ?? "—" },
        { key: "descripcion", header: "Descripción", render: (m: any) => m.descripcion ?? "—" },
        { key: "debitos", header: "Débitos", numeric: true, render: (m: any) => m.debitos ?? "—" },
        { key: "creditos", header: "Créditos", numeric: true, render: (m: any) => m.creditos ?? "—" },
        { key: "saldo", header: "Saldo", numeric: true, render: (m: any) => m.saldo ?? "—" },
        { key: "contacto", header: "Contacto", render: (m: any) => m.contacto ?? "—" },
      ];
    case "efectivo":
      return [
        { key: "fecha", header: "Fecha", numeric: true, render: (m: any) => m.fecha ?? "—" },
        { key: "cuenta", header: "Cuenta", render: (m: any) => m.cuenta ?? "—" },
        { key: "caja", header: "Caja", render: (m: any) => m.caja ?? "—" },
        { key: "numeroDocumento", header: "Nro. documento", numeric: true, render: (m: any) => m.numeroDocumento ?? "—" },
        { key: "importeImputado", header: "Importe imputado", numeric: true, render: (m: any) => m.importeImputado ?? "—" },
      ];
    case "valores-propios":
      return [
        { key: "numeroCheque", header: "Nro. cheque", numeric: true, render: (m: any) => m.numeroCheque ?? "—" },
        { key: "fechaEmision", header: "Emisión", numeric: true, render: (m: any) => m.fechaEmision ?? "—" },
        { key: "fechaVencimiento", header: "Vencimiento", numeric: true, render: (m: any) => m.fechaVencimiento ?? "—" },
        { key: "importe", header: "Importe", numeric: true, render: (m: any) => m.importe ?? "—" },
        { key: "cobrado", header: "Cobrado", render: (m: any) => m.cobrado ?? "—" },
        { key: "fechaCobro", header: "Fecha cobro", numeric: true, render: (m: any) => m.fechaCobro ?? "—" },
      ];
    case "valores-recibidos":
      return [
        { key: "numeroValor", header: "Nro. valor", numeric: true, render: (m: any) => m.numeroValor ?? "—" },
        { key: "banco", header: "Banco", render: (m: any) => m.banco ?? "—" },
        { key: "fechaEmision", header: "Emisión", numeric: true, render: (m: any) => m.fechaEmision ?? "—" },
        { key: "fechaVencimiento", header: "Vencimiento", numeric: true, render: (m: any) => m.fechaVencimiento ?? "—" },
        { key: "fechaCobro", header: "Cobro", numeric: true, render: (m: any) => m.fechaCobro ?? "—" },
        { key: "importe", header: "Importe", numeric: true, render: (m: any) => m.importe ?? "—" },
        { key: "destino", header: "Destino", render: (m: any) => m.destino ?? "—" },
      ];
    case "tarjetas":
      return [
        { key: "fechaCompra", header: "Fecha compra", numeric: true, render: (m: any) => m.fechaCompra ?? "—" },
        { key: "detalle", header: "Detalle", render: (m: any) => m.detalle ?? "—" },
        { key: "importe", header: "Importe", numeric: true, render: (m: any) => m.importe ?? "—" },
        { key: "numeroDocumento", header: "Nro. documento", numeric: true, render: (m: any) => m.numeroDocumento ?? "—" },
      ];
  }
}

function idFieldFor(medio: Medio): string {
  switch (medio) {
    case "bna":
      return "idMovimientoBNA";
    case "galicia":
      return "idMovimiento";
    case "efectivo":
      return "idPagoEfectivo";
    case "valores-propios":
    case "valores-recibidos":
      return "idValor";
    case "tarjetas":
      return "idLineaConsumo";
  }
}

export function MovimientosPorMedio({ medio }: { medio: Medio }) {
  const [fechaDesde, setFechaDesde] = useState("");
  const [fechaHasta, setFechaHasta] = useState("");
  const [page, setPage] = useState(1);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const pageSize = 50;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["tesoreria-movimientos", medio, fechaDesde, fechaHasta, page, pageSize],
    queryFn: () =>
      fetchMovimientos(medio, {
        fechaDesde: fechaDesde || undefined,
        fechaHasta: fechaHasta || undefined,
        page,
        pageSize,
      }),
  });

  const idField = idFieldFor(medio);

  const columns: DataTableColumn<MovimientoPorMedio[typeof medio]>[] = [
    ...columnsFor(medio).map((col) => ({
      key: col.key,
      header: col.header,
      numeric: col.numeric,
      render: col.render,
    })),
    {
      key: "referencia",
      header: "Referencia de origen",
      render: (item: any) => {
        const id = item[idField] as number;
        return expandedId === id ? (
          <ReferenciaOrigen medio={medio} idMovimiento={id} />
        ) : (
          <button className="text-finance underline" onClick={() => setExpandedId(id)}>
            Ver referencia
          </button>
        );
      },
    },
  ];

  return (
    <div className="space-y-4">
      <FilterBar onSubmit={(e) => e.preventDefault()}>
        <FilterField label="Fecha desde">
          <input
            type="date"
            className={filterInputClass}
            value={fechaDesde}
            onChange={(e) => {
              setPage(1);
              setFechaDesde(e.target.value);
            }}
          />
        </FilterField>
        <FilterField label="Fecha hasta">
          <input
            type="date"
            className={filterInputClass}
            value={fechaHasta}
            onChange={(e) => {
              setPage(1);
              setFechaHasta(e.target.value);
            }}
          />
        </FilterField>
      </FilterBar>

      {isLoading && <LoadingState />}
      {isError && (
        <ErrorState message="Ocurrió un error al buscar movimientos." onRetry={() => refetch()} />
      )}

      {data && (
        <DataTable
          columns={columns}
          rows={data.items}
          keyField={(item: any) => item[idField]}
          emptyMessage={`Sin movimientos para ${MEDIO_LABELS[medio]} en este rango.`}
          page={data.page}
          pageSize={data.pageSize}
          total={data.total}
          onPageChange={setPage}
        />
      )}
    </div>
  );
}

export { MEDIO_LABELS };
