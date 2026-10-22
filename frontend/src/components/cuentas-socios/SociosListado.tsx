"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { fetchSocios, type SocioConSaldo } from "@/services/cuentasSociosApi";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatCantidad, formatFecha, formatMoneda } from "@/lib/format";

function tono(v: number) {
  return v > 0 ? "text-status-danger" : v < 0 ? "text-status-success" : "";
}

const COLUMNS: DataTableColumn<SocioConSaldo>[] = [
  {
    key: "nombre",
    header: "Socio",
    sortValue: (s) => s.nombre,
    render: (s) => (
      <Link href={`/finanzas/cuentas-socios/${s.idSocio}`} className="text-finance underline">
        {s.nombre}
      </Link>
    ),
  },
  {
    key: "kg",
    header: "Kg. Carne",
    align: "right",
    numeric: true,
    sortValue: (s) => s.actualizada?.kgCarne ?? 0,
    render: (s) => <span className={tono(s.actualizada?.kgCarne ?? 0)}>{formatCantidad(s.actualizada?.kgCarne ?? 0)} kg</span>,
  },
  {
    key: "usd",
    header: "Dólares",
    align: "right",
    numeric: true,
    sortValue: (s) => s.actualizada?.dolares ?? 0,
    render: (s) => <span className={tono(s.actualizada?.dolares ?? 0)}>{formatMoneda(s.actualizada?.dolares ?? 0, "Dolares")}</span>,
  },
  {
    key: "actualizada",
    header: "Deuda actualizada",
    align: "right",
    numeric: true,
    sortValue: (s) => s.actualizada?.deudaActualizada ?? 0,
    render: (s) => (
      <span className={`font-semibold ${tono(s.actualizada?.deudaActualizada ?? 0)}`}>
        {formatMoneda(s.actualizada?.deudaActualizada ?? 0)}
      </span>
    ),
  },
  {
    key: "mutuo",
    header: "Mutuo (US$)",
    align: "right",
    numeric: true,
    sortValue: (s) => s.actualizada?.mutuoUSD ?? 0,
    render: (s) =>
      s.actualizada?.mutuoUSD ? (
        <span className={tono(s.actualizada.mutuoUSD)} title={formatMoneda(s.actualizada.mutuoPesos)}>
          {formatMoneda(s.actualizada.mutuoUSD, "Dolares")}
        </span>
      ) : (
        "—"
      ),
  },
  {
    key: "saldo",
    header: "Saldo en pesos históricos",
    align: "right",
    numeric: true,
    sortValue: (s) => s.saldo,
    render: (s) => <span className="text-ink-secondary">{formatMoneda(s.saldo)}</span>,
  },
];

/** Catálogo cerrado de socios/condominio con su deuda actualizada como la
 * planilla Cajas Giamigli (kg × novillo + US$ × dólar de hoy). Positivo: el
 * socio le debe a la empresa; negativo: a favor del socio. */
export function SociosListado() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["cuentas-socios"],
    queryFn: fetchSocios,
  });
  const cot = data?.socios[0]?.actualizada;

  return (
    <div className="space-y-4">
      {isLoading && <LoadingState />}
      {isError && <ErrorState message="Ocurrió un error al obtener los socios." onRetry={() => refetch()} />}

      {cot && (
        <p className="text-sm text-ink-secondary">
          Índice novillo {formatMoneda(cot.novillo)} ({cot.fechaNovillo ? formatFecha(cot.fechaNovillo) : "—"}) · Dólar BNA billete{" "}
          {formatMoneda(cot.dolar)} ({cot.fechaDolar ? formatFecha(cot.fechaDolar) : "—"}). Positivo: el socio le debe a la empresa;
          negativo: a favor del socio.
        </p>
      )}

      {data && (
        <DataTable
          columns={COLUMNS}
          rows={data.socios}
          keyField={(s) => s.idSocio}
          emptyMessage="No hay socios cargados."
          page={1}
          pageSize={Math.max(data.socios.length, 1)}
          total={data.socios.length}
          onPageChange={() => {}}
        />
      )}
    </div>
  );
}
