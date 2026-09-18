"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { fetchTarjetas } from "@/services/tarjetasApi";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { ErrorState, LoadingState } from "@/components/ui/States";
import type { Tarjeta } from "@/services/tarjetasApi";

const COLUMNS: DataTableColumn<Tarjeta>[] = [
  {
    key: "nombre",
    header: "Tarjeta",
    render: (t) => (
      <Link className="text-finance underline" href={`/finanzas/tarjetas/${t.idTarjeta}/cuenta-corriente`}>
        {t.nombre}
      </Link>
    ),
  },
  { key: "banco", header: "Banco", render: (t) => t.banco ?? "—" },
  {
    key: "activa",
    header: "Estado",
    render: (t) => (
      <span className={t.activa ? "text-status-success" : "text-ink-secondary"}>{t.activa ? "Activa" : "Inactiva"}</span>
    ),
  },
];

/** Catálogo de tarjetas (Historia 4) — solo lectura. Cada fila linkea a
 * la cuenta corriente de esa tarjeta (Historia 2). */
export function TarjetasListado() {
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["tarjetas", "catalogo"], queryFn: () => fetchTarjetas(false) });

  if (isLoading) return <LoadingState />;
  if (isError) return <ErrorState message="Ocurrió un error al cargar el catálogo de tarjetas." onRetry={() => refetch()} />;

  const rows = data ?? [];
  return (
    <DataTable
      columns={COLUMNS}
      rows={rows}
      keyField={(t) => t.idTarjeta}
      emptyMessage="No hay tarjetas cargadas."
      page={1}
      pageSize={rows.length || 1}
      total={rows.length}
      onPageChange={() => {}}
    />
  );
}
