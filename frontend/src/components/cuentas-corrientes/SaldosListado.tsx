"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { fetchSaldos, urlExportarSaldos, type SaldoContacto } from "@/services/cuentasCorrientesApi";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatMoneda } from "@/lib/format";

const COLUMNS: DataTableColumn<SaldoContacto>[] = [
  {
    key: "razonSocial",
    header: "Razón social",
    sortValue: (s) => s.razonSocial ?? "",
    render: (s) => (
      <Link
        href={`/finanzas/cuentas-corrientes?idContacto=${s.idContacto}&razonSocial=${encodeURIComponent(s.razonSocial ?? "")}`}
        className="text-finance underline"
      >
        {s.razonSocial ?? "—"}
      </Link>
    ),
  },
  {
    key: "saldoParcial",
    header: "Saldo",
    align: "right",
    numeric: true,
    sortValue: (s) => s.saldoParcial,
    render: (s) => (
      <span className={s.saldoParcial != null && s.saldoParcial < 0 ? "text-status-danger" : "text-status-success"}>
        {s.saldoParcial != null ? formatMoneda(s.saldoParcial) : "—"}
      </span>
    ),
  },
];

/** Saldo de todos los proveedores con movimientos, de una sola vez (014 US2). */
export function SaldosListado() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["cc-saldos"],
    queryFn: () => fetchSaldos("razonSocial"),
  });

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <a
          href={urlExportarSaldos("razonSocial")}
          className="rounded border border-border px-3 py-1.5 text-sm hover:bg-surface-sunken"
        >
          Exportar a Excel
        </a>
      </div>

      {isLoading && <LoadingState />}
      {isError && <ErrorState message="Ocurrió un error al obtener los saldos." onRetry={() => refetch()} />}

      {data && (
        <DataTable
          columns={COLUMNS}
          rows={data.items}
          keyField={(s) => s.idContacto}
          emptyMessage="No hay contactos con movimientos registrados."
          page={1}
          pageSize={Math.max(data.items.length, 1)}
          total={data.items.length}
          onPageChange={() => {}}
        />
      )}
    </div>
  );
}
