"use client";

import { useQuery } from "@tanstack/react-query";
import { Saldo } from "@/components/ui/Saldo";
import { SOCIO_DE_CONTACTO } from "@/components/ui/AvisoCuentaContacto";
import Link from "next/link";
import { useState } from "react";

import { fetchMovimientos, fetchSaldos, urlExportarSaldos, type SaldoContacto } from "@/services/cuentasCorrientesApi";
import { SideDrawer } from "@/components/ui/SideDrawer";
import { formatFecha } from "@/lib/format";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatMoneda } from "@/lib/format";

const cuentaUrl = (s: SaldoContacto) =>
  `/finanzas/cuentas-corrientes?idContacto=${s.idContacto}&razonSocial=${encodeURIComponent(s.razonSocial ?? "")}`;

/** Spec 051: resumen de la cuenta en el panel lateral (saldo y últimos movimientos), sin salir del listado. */
function ResumenCuenta({ s }: { s: SaldoContacto }) {
  const { data, isLoading } = useQuery({
    queryKey: ["saldos-panel", s.idContacto],
    queryFn: () => fetchMovimientos(s.idContacto, { page: 1, pageSize: 12, sortBy: "fecha", sortDir: "desc" }),
  });
  return (
    <div className="space-y-4">
      <div className="rounded-lg bg-surface-sunken/60 p-3">
        <p className="text-xs text-ink-secondary">Saldo</p>
        <p className="text-lg font-semibold"><Saldo valor={s.saldoParcial} negativo="Debemos" positivo="A favor nuestro" /></p>
        {s.saldoDolares != null && <p className="text-sm"><Saldo valor={s.saldoDolares} moneda="Dolares" negativo="Debemos" positivo="A favor nuestro" /></p>}
      </div>
      <div>
        <h3 className="mb-2 text-sm font-semibold text-ink-primary">Últimos movimientos</h3>
        {isLoading ? <LoadingState rows={5} /> : (
          <ul className="divide-y divide-border rounded-md border border-border text-sm">
            {(data?.items ?? []).map((m, i) => (
              <li key={i} className="flex items-baseline justify-between gap-3 px-3 py-1.5">
                <span className="min-w-0"><span className="text-ink-secondary">{formatFecha(m.fecha)}</span> · <span className="truncate">{m.documento ?? "—"} {m.numeroDocumento ?? ""}</span></span>
                <span className="font-data whitespace-nowrap">{m.deuda ? formatMoneda(m.deuda) : m.credito ? `− ${formatMoneda(m.credito)}` : "—"}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

const COLUMNS: DataTableColumn<SaldoContacto>[] = [
  {
    key: "razonSocial",
    header: "Razón social",
    sortValue: (s) => s.razonSocial ?? "",
    render: (s) => (
      <Link href={cuentaUrl(s)} className="font-medium text-ink-primary hover:text-finance hover:underline">
        {s.razonSocial ?? "—"}
        {SOCIO_DE_CONTACTO[s.idContacto] && <span className="ml-2 rounded-sm bg-surface-sunken px-1.5 text-xs text-ink-secondary" title="Su saldo en pesos no es deuda: ver la cuenta de socio">socio</span>}
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
      <Saldo valor={s.saldoParcial} negativo="Debemos" positivo="A favor nuestro" />
    ),
  },
  {
    key: "saldoDolares",
    header: "Saldo US$",
    align: "right",
    numeric: true,
    sortValue: (s) => s.saldoDolares ?? 0,
    render: (s) =>
      s.saldoDolares != null ? (
        <Saldo valor={s.saldoDolares} moneda="Dolares" negativo="Debemos" positivo="A favor nuestro" />
      ) : (
        ""
      ),
  },
];

/** Cuenta saldada: en pesos dentro de la tolerancia y, si la gobiernan los dólares, en US$ 0 (< us$ 1). */
function estaSaldada(s: SaldoContacto): boolean {
  if (s.moneda === "Dolares" || s.moneda === "Mixta") return Math.abs(s.saldoDolares ?? 0) < 1;
  return Math.abs(s.saldoParcial ?? 0) <= TOLERANCIA_SALDADA;
}

// Saldos dentro de +/- $500 se consideran redondeo de procesamiento, no
// deuda real (pedido explícito del usuario, 2026-09-28).
const TOLERANCIA_SALDADA = 500;

/** Saldo de todos los proveedores con movimientos, de una sola vez (014 US2).
 * Por defecto solo muestra las cuentas no saldadas (saldo con módulo mayor
 * a la tolerancia de redondeo) — el listado completo, incluidas las
 * cuentas en $0, sigue disponible destildando el filtro. */
export function SaldosListado() {
  const [soloNoSaldadas, setSoloNoSaldadas] = useState(true);
  const [abierto, setAbierto] = useState<SaldoContacto | null>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["cc-saldos"],
    queryFn: () => fetchSaldos("razonSocial"),
  });

  const filas = data
    ? soloNoSaldadas
      ? data.items.filter((s) => !estaSaldada(s))
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
          onRowClick={setAbierto}
          selectedKey={abierto?.idContacto}
          rowActions={(s) => [{ label: "Ver resumen", onClick: () => setAbierto(s) }, { label: "Abrir cuenta corriente", href: cuentaUrl(s) }]}
        />
      )}
      <SideDrawer open={abierto != null} onClose={() => setAbierto(null)} title={abierto?.razonSocial ?? ""} maxWidthClass="max-w-lg"
        verCompleto={abierto ? cuentaUrl(abierto) : undefined}>
        {abierto && <ResumenCuenta s={abierto} />}
      </SideDrawer>
    </div>
  );
}
