"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { fetchSocios, type SocioConSaldo } from "@/services/cuentasSociosApi";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatMoneda } from "@/lib/format";

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
    key: "saldo",
    header: "Saldo (a favor de la empresa)",
    align: "right",
    numeric: true,
    sortValue: (s) => s.saldo,
    render: (s) => (
      <span className={s.saldo > 0 ? "text-status-danger" : s.saldo < 0 ? "text-status-success" : ""}>
        {formatMoneda(s.saldo)}
      </span>
    ),
  },
];

/** Catálogo cerrado de 4 socios/condominio con su saldo actual (021 US2). */
export function SociosListado() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["cuentas-socios"],
    queryFn: fetchSocios,
  });

  return (
    <div className="space-y-4">
      {isLoading && <LoadingState />}
      {isError && <ErrorState message="Ocurrió un error al obtener los socios." onRetry={() => refetch()} />}

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
