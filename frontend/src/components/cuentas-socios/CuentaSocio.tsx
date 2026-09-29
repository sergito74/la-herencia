"use client";

import { useQueryClient, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import {
  anularMovimiento,
  fetchDetalleSocio,
  registrarDevolucion,
  type MovimientoCuentaSocio,
} from "@/services/cuentasSociosApi";
import { AsignarGastoForm } from "@/components/cuentas-socios/AsignarGastoForm";
import { SoloLectura } from "@/components/auth/SoloLectura";
import { ApiError } from "@/services/apiClient";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { filterInputClass } from "@/components/ui/FilterBar";
import { KpiCard } from "@/components/ui/KpiCard";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { MoneyInput } from "@/components/ui/MoneyInput";
import { useToast } from "@/components/ui/Toast";
import { formatMoneda } from "@/lib/format";

const MEDIOS_DEVOLUCION = ["Transferencia", "Efectivo", "Cheque", "Otro"];

function OrigenMovimientoSocio({ m }: { m: MovimientoCuentaSocio }) {
  if (m.tipo === "Devolucion") {
    return <span>Devolución{m.medio ? ` (${m.medio})` : ""}</span>;
  }
  if (m.huerfano) {
    return <span className="text-status-danger">Compra particular #{m.idOrigen} (ya no existe)</span>;
  }
  return (
    <span>
      {m.proveedorOrigen ?? "Compra particular"}
      {m.numeroDocumentoOrigen ? ` — ${m.numeroDocumentoOrigen}` : ""}
    </span>
  );
}

/** Cuenta corriente de un socio: saldo + movimientos (021 US2), con
 * anulación en un paso (US1/US3) y registro de devoluciones (US3). Un
 * saldo positivo significa que el socio le debe a la empresa. */
export function CuentaSocio({ idSocio }: { idSocio: number }) {
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const queryKey = ["cuenta-socio", idSocio];

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey,
    queryFn: () => fetchDetalleSocio(idSocio),
  });

  const [mostrarDevolucion, setMostrarDevolucion] = useState(false);
  const [importe, setImporte] = useState(0);
  const [fecha, setFecha] = useState(() => new Date().toISOString().slice(0, 10));
  const [medio, setMedio] = useState(MEDIOS_DEVOLUCION[0]);
  const [motivo, setMotivo] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function recargar() {
    await queryClient.invalidateQueries({ queryKey });
    await queryClient.invalidateQueries({ queryKey: ["cuentas-socios"] });
  }

  async function anular(m: MovimientoCuentaSocio) {
    const motivoAnulacion = window.prompt("Motivo de la anulación:");
    if (!motivoAnulacion) return;
    try {
      await anularMovimiento(m.idMovimiento, motivoAnulacion);
      showToast("Movimiento anulado.", "success");
      await recargar();
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "Error al anular el movimiento.", "danger");
    }
  }

  async function confirmarDevolucion() {
    setError(null);
    if (importe <= 0) {
      setError("El importe debe ser mayor a $0.");
      return;
    }
    if (!motivo.trim()) {
      setError("El motivo es obligatorio.");
      return;
    }
    setGuardando(true);
    try {
      await registrarDevolucion(idSocio, { importe, fecha, medio, motivo });
      showToast("Devolución registrada.", "success");
      setMostrarDevolucion(false);
      setImporte(0);
      setMotivo("");
      await recargar();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Error al registrar la devolución.");
    } finally {
      setGuardando(false);
    }
  }

  const columns: DataTableColumn<MovimientoCuentaSocio>[] = [
    { key: "fecha", header: "Fecha", sortValue: (m) => m.fecha, render: (m) => m.fecha?.slice(0, 10) ?? "—" },
    { key: "tipo", header: "Tipo", render: (m) => (m.tipo === "AsignacionGasto" ? "Gasto asignado" : "Devolución") },
    { key: "origen", header: "Origen", render: (m) => <OrigenMovimientoSocio m={m} /> },
    {
      key: "importe",
      header: "Importe",
      align: "right",
      numeric: true,
      sortValue: (m) => m.importe,
      render: (m) => (
        <span className={m.tipo === "AsignacionGasto" ? "text-status-danger" : "text-status-success"}>
          {formatMoneda(m.importe)}
        </span>
      ),
    },
    {
      key: "estado",
      header: "Estado",
      render: (m) =>
        m.anulada ? (
          <span className="text-ink-secondary line-through" title={m.motivoAnulacion ?? ""}>
            Anulado{m.motivoAnulacion ? `: ${m.motivoAnulacion}` : ""}
          </span>
        ) : (
          <SoloLectura>
            <button type="button" onClick={() => anular(m)} className="text-sm text-finance underline">
              Anular
            </button>
          </SoloLectura>
        ),
    },
  ];

  return (
    <div className="space-y-6">
      {isLoading && <LoadingState />}
      {isError && <ErrorState message="Ocurrió un error al obtener la cuenta del socio." onRetry={() => refetch()} />}

      {data && (
        <>
          <div className="flex items-center justify-between gap-4 rounded-md border border-border bg-surface p-4">
            <div>
              <h2 className="text-lg font-semibold text-ink-primary">{data.nombre}</h2>
              <p className="text-sm text-ink-secondary">
                Saldo positivo: el socio le debe a la empresa. Saldo negativo: a favor del socio.
              </p>
            </div>
            <KpiCard
              label="Saldo"
              value={formatMoneda(data.saldo)}
              tone={data.saldo > 0 ? "danger" : data.saldo < 0 ? "success" : "neutral"}
            />
          </div>

          <div className="flex flex-wrap gap-3">
            <AsignarGastoForm idSocio={idSocio} onAsignado={recargar} />
            <SoloLectura>
              <button
                type="button"
                onClick={() => setMostrarDevolucion((v) => !v)}
                className="rounded border border-border px-3 py-1.5 text-sm hover:bg-surface-sunken"
              >
                {mostrarDevolucion ? "Cancelar devolución" : "Registrar devolución…"}
              </button>
            </SoloLectura>
          </div>

          {mostrarDevolucion && (
            <div className="space-y-2 rounded-md border border-border bg-surface-sunken p-4">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
                <label className="text-sm">
                  Importe
                  <MoneyInput className={filterInputClass} moneda="Pesos" value={importe} onChange={setImporte} />
                </label>
                <label className="text-sm">
                  Fecha
                  <input
                    type="date"
                    className={filterInputClass}
                    value={fecha}
                    onChange={(e) => setFecha(e.target.value)}
                  />
                </label>
                <label className="text-sm">
                  Medio
                  <select className={filterInputClass} value={medio} onChange={(e) => setMedio(e.target.value)}>
                    {MEDIOS_DEVOLUCION.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="text-sm sm:col-span-1">
                  Motivo
                  <input
                    className={filterInputClass}
                    value={motivo}
                    onChange={(e) => setMotivo(e.target.value)}
                    placeholder="Ej: pago en efectivo"
                  />
                </label>
              </div>
              {error && <p className="text-sm text-status-danger">{error}</p>}
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  disabled={guardando}
                  onClick={confirmarDevolucion}
                  className="rounded bg-finance px-3 py-1.5 text-sm text-white disabled:opacity-50"
                >
                  {guardando ? "Guardando…" : "Confirmar"}
                </button>
              </div>
            </div>
          )}

          <DataTable
            columns={columns}
            rows={data.movimientos}
            keyField={(m) => m.idMovimiento}
            emptyMessage="Sin movimientos registrados para este socio."
            page={1}
            pageSize={Math.max(data.movimientos.length, 1)}
            total={data.movimientos.length}
            onPageChange={() => {}}
          />
        </>
      )}

      <Link href="/finanzas/cuentas-socios" className="text-sm text-finance underline">
        Volver al listado de socios
      </Link>
    </div>
  );
}
