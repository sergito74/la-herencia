"use client";
import Link from "next/link";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/services/apiClient";
import { registrarPagoAdicionalCaja } from "@/services/remuneracionesApi";
import { SoloLectura } from "@/components/auth/SoloLectura";
import { formatFecha, formatMoneda } from "@/lib/format";
import { useToast } from "@/components/ui/Toast";

type PagoCajaInfo = {
  IdMovimiento: number;
  Fecha: string;
  Caja: string;
  Cuenta: string;
  Importe: number;
  Concepto: string;
  IdPagoEfectivo: number | null;
};

type Calculo = {
  netoRecibo: number;
  adicional: number;
  feriados: number;
  redondeo: number;
  totalAdicional: number;
  registrado: number;
  totalACobrar: number;
  periodo: string;
  adicionalSeparado: number | null;
  registradoSeparado: number;
  puedeGuardar: boolean;
  pagoCaja: PagoCajaInfo | null;
};

export function AdicionalSierra({
  idSalario,
  fechaSugerida,
}: {
  idSalario: number;
  fechaSugerida?: string;
}) {
  const { showToast } = useToast();
  const [abierto, setAbierto] = useState(false);
  const [error, setError] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [fechaPagoCaja, setFechaPagoCaja] = useState(
    fechaSugerida ?? new Intl.DateTimeFormat("sv-SE", { timeZone: "America/Argentina/Buenos_Aires" }).format(new Date())
  );
  const qc = useQueryClient();
  const ruta = `/api/remuneraciones/${idSalario}/adicional`;
  const {
    data: d,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["adicional-sierra", idSalario],
    queryFn: () => apiGet<Calculo>(ruta),
    enabled: abierto,
  });

  const total = d?.totalAdicional ?? 0;

  async function guardar() {
    setOcupado(true);
    setError("");
    try {
      await apiPost(ruta, {});
      await refetch();
      await qc.invalidateQueries({ queryKey: ["remuneraciones"] });
      await qc.invalidateQueries({ queryKey: ["trabajos-eventuales"] });
      showToast("Adicional guardado en la liquidación.", "success");
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo guardar el adicional");
    } finally {
      setOcupado(false);
    }
  }

  async function pagarCaja() {
    if (!fechaPagoCaja) {
      setError("Ingresá la fecha para el asiento de caja.");
      return;
    }
    setOcupado(true);
    setError("");
    try {
      await registrarPagoAdicionalCaja(idSalario, {
        fecha: fechaPagoCaja,
        cuenta: "B",
      });
      await refetch();
      await qc.invalidateQueries({ queryKey: ["remuneraciones"] });
      await qc.invalidateQueries({ queryKey: ["caja-operativa"] });
      showToast("Pago registrado en Caja Giamigli SA (Cuenta B) y cuenta corriente del empleado.", "success");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al registrar el pago en caja");
    } finally {
      setOcupado(false);
    }
  }

  return (
    <div className="min-w-36">
      <button
        type="button"
        className="text-finance underline"
        onClick={() => setAbierto(!abierto)}
      >
        {abierto ? "Cerrar adicional" : "Calcular / Ver adicional"}
      </button>
      {abierto && (
        <div className="mt-2 min-w-80 space-y-2 rounded border border-border bg-surface p-3 text-xs whitespace-normal shadow-sm">
          {isLoading ? (
            <p>Cargando…</p>
          ) : isError || !d ? (
            <p>
              No se pudo consultar el adicional.{" "}
              <button className="underline" onClick={() => refetch()}>
                Reintentar
              </button>
            </p>
          ) : (
            <>
              <div className="border-b border-border pb-1 font-semibold text-ink">
                Fuera de recibo · {d.periodo}
              </div>
              <p>Neto del recibo: <span className="font-medium">{formatMoneda(d.netoRecibo)}</span></p>
              <p>Adicional 30%: {formatMoneda(d.adicional)}</p>
              <p>Feriados 8,5%: {formatMoneda(d.feriados)}</p>
              <p className="text-ink-secondary italic">
                Cada parte redondea al múltiplo de $5 más cercano.
              </p>
              <p>Redondeo a centena siguiente: {formatMoneda(d.redondeo)}</p>
              <p className="rounded bg-surface-sunken p-1.5 text-sm">
                <strong>Total adicional (efectivo): {formatMoneda(total)}</strong>
              </p>
              <p className="font-semibold text-ink">
                Total a cobrar (mano): {formatMoneda(d.netoRecibo + total)}
              </p>
              <p className="text-ink-secondary">
                Adicional ya en liquidación: {formatMoneda(d.registrado + d.registradoSeparado)}
              </p>

              {d.adicionalSeparado && (
                <p>
                  Registrado por separado.{" "}
                  <Link
                    className="text-finance underline"
                    href={`/personal/remuneraciones?empleado=Marcelo%20Sierra&highlight=${d.adicionalSeparado}`}
                  >
                    Ver adicional registrado
                  </Link>
                </p>
              )}

              <SoloLectura>
                {d.puedeGuardar && d.registrado !== total && (
                  <button
                    type="button"
                    disabled={ocupado || total <= 0}
                    className="rounded bg-finance px-3 py-1.5 text-white disabled:opacity-50"
                    onClick={guardar}
                  >
                    {ocupado ? "Guardando…" : "Guardar adicional en liquidación"}
                  </button>
                )}
              </SoloLectura>

              {/* Asiento de Caja Efectivo de Giamigli SA */}
              <div className="mt-3 border-t border-border pt-2">
                <div className="font-semibold text-ink">
                  Pago en efectivo · Caja Giamigli SA (Cuenta B)
                </div>
                {d.pagoCaja ? (
                  <div className="mt-1 rounded bg-green-50 p-2 text-green-900 border border-green-200 space-y-1">
                    <p className="font-medium">✓ Pago registrado en Caja Efectivo</p>
                    <p>Fecha: {formatFecha(d.pagoCaja.Fecha)} · Importe: {formatMoneda(Math.abs(d.pagoCaja.Importe))}</p>
                    <p className="text-[11px] text-green-700">{d.pagoCaja.Concepto}</p>
                    <Link
                      className="inline-block text-finance underline text-xs mt-1"
                      href={`/finanzas/cajas-efectivo/giamigli-sa?highlight=${d.pagoCaja.IdMovimiento}`}
                    >
                      Ver movimiento en Caja Giamigli SA
                    </Link>
                  </div>
                ) : (
                  <div className="mt-1 space-y-2 rounded bg-amber-50 p-2 border border-amber-200 text-amber-900">
                    <p className="text-xs">
                      Pendiente de preparar y asentar en la caja de efectivo.
                    </p>
                    <label className="block text-xs">
                      Fecha del pago en efectivo:
                      <input
                        type="date"
                        className="mt-1 block w-full rounded border border-border bg-white px-2 py-1 text-ink"
                        value={fechaPagoCaja}
                        onChange={(e) => setFechaPagoCaja(e.target.value)}
                      />
                    </label>
                    <SoloLectura>
                      <button
                        type="button"
                        disabled={ocupado || total <= 0}
                        className="w-full rounded bg-amber-700 px-3 py-1.5 font-medium text-white hover:bg-amber-800 disabled:opacity-50"
                        onClick={pagarCaja}
                      >
                        {ocupado ? "Asentando en caja…" : `Hacer asiento de caja por ${formatMoneda(total)}`}
                      </button>
                    </SoloLectura>
                  </div>
                )}
              </div>
            </>
          )}
          {error && (
            <p role="alert" className="text-red-700 font-medium">
              {error}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
