"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

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

// Saldos dentro de +/- $500 se consideran redondeo de procesamiento, no
// deuda real (pedido explícito del usuario, 2026-09-28).
const TOLERANCIA_SALDADA = 500;

/** Saldo de todos los proveedores con movimientos, de una sola vez (014 US2).
 * Por defecto solo muestra las cuentas no saldadas (saldo con módulo mayor
 * a la tolerancia de redondeo) — el listado completo, incluidas las
 * cuentas en $0, sigue disponible destildando el filtro. */
export function SaldosListado() {
  const [soloNoSaldadas, setSoloNoSaldadas] = useState(true);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["cc-saldos"],
    queryFn: () => fetchSaldos("razonSocial"),
  });

  const filas = data
    ? soloNoSaldadas
      ? data.items.filter((s) => Math.abs(s.saldoParcial ?? 0) > TOLERANCIA_SALDADA)
      : data.items
    : [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={soloNoSaldadas}
            onChange={(e) => setSoloNoSaldadas(e.target.checked)}
          />
          Solo cuentas no saldadas
        </label>
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
          rows={filas}
          keyField={(s) => s.idContacto}
          emptyMessage={
            soloNoSaldadas
              ? "No hay cuentas pendientes — todas están saldadas."
              : "No hay contactos con movimientos registrados."
          }
          page={1}
          pageSize={Math.max(filas.length, 1)}
          total={filas.length}
          onPageChange={() => {}}
        />
      )}
    </div>
  );
}
