"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import {
  fetchMovimientos,
  type Medio,
  type MovimientoPorMedio,
} from "@/services/tesoreriaApi";
import { ReferenciaOrigen } from "@/components/tesoreria/ReferenciaOrigen";

const MEDIO_LABELS: Record<Medio, string> = {
  bna: "Banco Nación",
  galicia: "Galicia",
  efectivo: "Pagos en efectivo",
  "valores-propios": "Valores propios",
  "valores-recibidos": "Valores recibidos",
  tarjetas: "Tarjetas",
};

interface ColumnDef<M extends Medio> {
  header: string;
  render: (item: MovimientoPorMedio[M]) => React.ReactNode;
}

function columnsFor<M extends Medio>(medio: M): ColumnDef<M>[] {
  switch (medio) {
    case "bna":
      return [
        { header: "Fecha/Hora", render: (m: any) => m.fechaHora ?? "—" },
        { header: "Concepto", render: (m: any) => m.concepto ?? "—" },
        { header: "Importe", render: (m: any) => m.importe ?? "—" },
        { header: "Contacto", render: (m: any) => m.contacto ?? "—" },
      ] as ColumnDef<M>[];
    case "galicia":
      return [
        { header: "Fecha", render: (m: any) => m.fecha ?? "—" },
        { header: "Descripción", render: (m: any) => m.descripcion ?? "—" },
        { header: "Débitos", render: (m: any) => m.debitos ?? "—" },
        { header: "Créditos", render: (m: any) => m.creditos ?? "—" },
        { header: "Saldo", render: (m: any) => m.saldo ?? "—" },
        { header: "Contacto", render: (m: any) => m.contacto ?? "—" },
      ] as ColumnDef<M>[];
    case "efectivo":
      return [
        { header: "Fecha", render: (m: any) => m.fecha ?? "—" },
        { header: "Cuenta", render: (m: any) => m.cuenta ?? "—" },
        { header: "Caja", render: (m: any) => m.caja ?? "—" },
        { header: "Nro. documento", render: (m: any) => m.numeroDocumento ?? "—" },
        { header: "Importe imputado", render: (m: any) => m.importeImputado ?? "—" },
      ] as ColumnDef<M>[];
    case "valores-propios":
      return [
        { header: "Nro. cheque", render: (m: any) => m.numeroCheque ?? "—" },
        { header: "Emisión", render: (m: any) => m.fechaEmision ?? "—" },
        { header: "Vencimiento", render: (m: any) => m.fechaVencimiento ?? "—" },
        { header: "Importe", render: (m: any) => m.importe ?? "—" },
        { header: "Cobrado", render: (m: any) => m.cobrado ?? "—" },
        { header: "Fecha cobro", render: (m: any) => m.fechaCobro ?? "—" },
      ] as ColumnDef<M>[];
    case "valores-recibidos":
      return [
        { header: "Nro. valor", render: (m: any) => m.numeroValor ?? "—" },
        { header: "Banco", render: (m: any) => m.banco ?? "—" },
        { header: "Emisión", render: (m: any) => m.fechaEmision ?? "—" },
        { header: "Vencimiento", render: (m: any) => m.fechaVencimiento ?? "—" },
        { header: "Cobro", render: (m: any) => m.fechaCobro ?? "—" },
        { header: "Importe", render: (m: any) => m.importe ?? "—" },
        { header: "Destino", render: (m: any) => m.destino ?? "—" },
      ] as ColumnDef<M>[];
    case "tarjetas":
      return [
        { header: "Fecha compra", render: (m: any) => m.fechaCompra ?? "—" },
        { header: "Detalle", render: (m: any) => m.detalle ?? "—" },
        { header: "Importe", render: (m: any) => m.importe ?? "—" },
        { header: "Nro. documento", render: (m: any) => m.numeroDocumento ?? "—" },
      ] as ColumnDef<M>[];
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

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["tesoreria-movimientos", medio, fechaDesde, fechaHasta, page, pageSize],
    queryFn: () =>
      fetchMovimientos(medio, {
        fechaDesde: fechaDesde || undefined,
        fechaHasta: fechaHasta || undefined,
        page,
        pageSize,
      }),
  });

  const columns = columnsFor(medio);
  const idField = idFieldFor(medio);
  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.pageSize)) : 1;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-4 rounded-lg border border-slate-200 bg-white p-4">
        <label className="flex flex-col gap-1 text-sm">
          Fecha desde
          <input
            type="date"
            className="rounded border border-slate-300 px-2 py-1"
            value={fechaDesde}
            onChange={(e) => {
              setPage(1);
              setFechaDesde(e.target.value);
            }}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Fecha hasta
          <input
            type="date"
            className="rounded border border-slate-300 px-2 py-1"
            value={fechaHasta}
            onChange={(e) => {
              setPage(1);
              setFechaHasta(e.target.value);
            }}
          />
        </label>
      </div>

      {isLoading && <p className="text-slate-600">Cargando…</p>}

      {isError && (
        <p className="text-red-700">
          Ocurrió un error al buscar movimientos: {(error as Error)?.message}
        </p>
      )}

      {data && data.items.length === 0 && (
        <p className="rounded border border-slate-200 bg-white p-6 text-center text-slate-600">
          Sin movimientos para {MEDIO_LABELS[medio]} en este rango.
        </p>
      )}

      {data && data.items.length > 0 && (
        <>
          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-100 text-left">
                <tr>
                  {columns.map((col) => (
                    <th key={col.header} className="px-3 py-2">
                      {col.header}
                    </th>
                  ))}
                  <th className="px-3 py-2">Referencia de origen</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.items.map((item) => {
                  const id = (item as any)[idField] as number;
                  return (
                    <tr key={id} className="hover:bg-slate-50">
                      {columns.map((col) => (
                        <td key={col.header} className="px-3 py-2">
                          {col.render(item)}
                        </td>
                      ))}
                      <td className="px-3 py-2">
                        {expandedId === id ? (
                          <ReferenciaOrigen medio={medio} idMovimiento={id} />
                        ) : (
                          <button
                            className="text-blue-700 underline"
                            onClick={() => setExpandedId(id)}
                          >
                            Ver referencia
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between text-sm text-slate-600">
            <span>
              Página {data.page} de {totalPages} — {data.total} movimientos
            </span>
            <div className="flex gap-2">
              <button
                className="rounded border border-slate-300 px-3 py-1 disabled:opacity-40"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Anterior
              </button>
              <button
                className="rounded border border-slate-300 px-3 py-1 disabled:opacity-40"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Siguiente
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export { MEDIO_LABELS };
