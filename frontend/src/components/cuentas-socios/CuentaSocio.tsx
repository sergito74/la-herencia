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
import { SideDrawer } from "@/components/ui/SideDrawer";
import { AsientoSocioForm } from "./AsientoSocioForm";
import { EfectivoSocioForm } from "./EfectivoSocioForm";
import { ControlBancoSocio } from "./ControlBancoSocio";
import { ApiError } from "@/services/apiClient";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { filterInputClass } from "@/components/ui/FilterBar";
import { KpiCard } from "@/components/ui/KpiCard";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { MoneyInput } from "@/components/ui/MoneyInput";
import { useToast } from "@/components/ui/Toast";
import { formatCantidad, formatMoneda, formatFecha } from "@/lib/format";

const MEDIOS_DEVOLUCION = ["Transferencia", "Efectivo", "Cheque", "Otro"];

/** De dónde sale el movimiento, en palabras (nunca el nombre interno del origen). */
const ORIGENES: Record<string, string> = {
  Galicia: "Débito Galicia",
  "Banco Nacion": "Débito Banco Nación",
  BNACondominio036: "Débito Banco Nación (Condominio)",
  PagosEfectivo: "Pago en efectivo",
  TarjetaLineaConsumo: "Consumo con tarjeta",
  ImpuestoParticular: "Impuesto particular",
  Caja038: "Caja de efectivo",
  CajaGiamigli036: "Caja de efectivo",
  CondominioHist036: "Condominio LSC",
  Mutuo2018: "Mutuo 2018",
  PagoBalance2025: "Pago balance 2025",
  ArcaGaliciaLucy036: "Débito Galicia personal",
  // Vínculo documental (10/11/2026): el socio pagó un gasto de Giamigli; apunta al comprobante, no mueve cuentas.
  Impuestos: "Pagó el socio · obligación de impuesto",
  Remuneraciones: "Pagó el socio · recibo de sueldo",
  Compras: "Pagó el socio · factura de compra",
  MercadoPago: "Mercado Pago Giamigli",
  TrabajosEventuales: "Pagó el socio · trabajo eventual",
};

/** Origen del movimiento, en una segunda línea chica debajo del concepto. */
function origenTexto(m: MovimientoCuentaSocio): string {
  if (m.huerfano) return "Compra particular (ya no existe)";
  if (m.origen === "CompraParticular")
    return `Compra particular · ${m.proveedorOrigen ?? "sin proveedor"}${m.numeroDocumentoOrigen ? ` — ${m.numeroDocumentoOrigen}` : ""}`;
  if (m.pagadoA && (!m.origen || !ORIGENES[m.origen]?.startsWith("Pagó el socio")))
    return `Pagó el socio · ${m.pagadoA}${m.medio ? ` · ${m.medio}` : ""}`;
  const base = m.origen ? ORIGENES[m.origen] ?? "Otro origen" : m.tipo === "Devolucion" ? "Devolución" : "Asiento manual";
  return m.medio && !base.includes(m.medio) ? `${base} · ${m.medio}` : base;
}

const debe = (m: MovimientoCuentaSocio) => m.tipo === "AsignacionGasto";
const vacio = <span className="text-ink-muted">—</span>;

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
  const [drawer, setDrawer] = useState<null | "asiento" | "efectivo" | MovimientoCuentaSocio>(null);
  const [buscar, setBuscar] = useState("");
  const [anio, setAnio] = useState("");
  const [verAnulados, setVerAnulados] = useState(false);
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

  // Saldo acumulado (kg y US$) en orden cronológico; no depende del filtro ni del orden de la tabla.
  const saldos = new Map<number, { kg: number; usd: number }>();
  {
    let kg = 0, usd = 0;
    for (const m of data?.movimientos ?? []) {
      if (!m.anulada) {
        const signo = debe(m) ? 1 : -1;
        kg += signo * (m.importeKgCarne ?? 0);
        usd += signo * (m.importeUSD ?? 0);
      }
      saldos.set(m.idMovimiento, { kg, usd });
    }
  }
  const celda = (m: MovimientoCuentaSocio, enDebe: boolean, v: number | null | undefined, formato: (v: number) => string) =>
    enDebe === debe(m) && v ? formato(v) : vacio;
  const pesos = (v: number) => formatMoneda(v);
  const dolares = (v: number) => formatMoneda(v, "Dolares");
  const kilos = (v: number) => `${formatCantidad(v)} kg`;
  const tono = (v: number) => (v > 0 ? "text-status-danger" : v < 0 ? "text-status-success" : "");
  const num = { align: "right" as const, numeric: true };

  const columns: DataTableColumn<MovimientoCuentaSocio>[] = [
    { key: "fecha", header: "Fecha", width: "w-[5.75rem]", sortValue: (m) => m.fecha, render: (m) => formatFecha(m.fecha) },
    {
      key: "concepto", header: "Concepto", wrap: true,
      render: (m) => (
        <div title={m.usuario ? `Cargado por ${m.usuario}` : undefined}>
          <div>{m.motivo ?? "—"}</div>
          <div className={`text-xs ${m.huerfano ? "text-status-danger" : "text-ink-muted"}`}>{origenTexto(m)}</div>
        </div>
      ),
    },
    { key: "debe", header: "Debe $", width: "w-[7.25rem]", ...num, render: (m) => celda(m, true, m.importe, pesos) },
    { key: "haber", header: "Haber $", width: "w-[7.25rem]", ...num, render: (m) => celda(m, false, m.importe, pesos) },
    { key: "debeUSD", header: "Debe US$", width: "w-[6rem]", ...num, render: (m) => celda(m, true, m.importeUSD, dolares) },
    { key: "haberUSD", header: "Haber US$", width: "w-[6rem]", ...num, render: (m) => celda(m, false, m.importeUSD, dolares) },
    { key: "debeKg", header: "Debe kg", width: "w-[5.5rem]", ...num, render: (m) => celda(m, true, m.importeKgCarne, kilos) },
    { key: "haberKg", header: "Haber kg", width: "w-[5.5rem]", ...num, render: (m) => celda(m, false, m.importeKgCarne, kilos) },
    {
      key: "saldoKg", header: "Saldo kg", width: "w-[7.25rem]", ...num,
      render: (m) => { const v = saldos.get(m.idMovimiento)?.kg ?? 0; return <span className={`font-medium ${tono(v)}`}>{kilos(v)}</span>; },
    },
    {
      key: "saldoUSD", header: "Saldo US$", width: "w-[7.25rem]", ...num,
      render: (m) => { const v = saldos.get(m.idMovimiento)?.usd ?? 0; return <span className={`font-medium ${tono(v)}`}>{dolares(v)}</span>; },
    },
    {
      key: "acciones", header: "", width: "w-[5.5rem]",
      render: (m) =>
        m.anulada ? (
          <span className="text-xs text-ink-secondary" title={m.motivoAnulacion ?? ""}>Anulado</span>
        ) : m.idOperacionCaja ? (
          <a className="text-xs text-finance underline" href="/finanzas/cajas" title="Se corrige o anula desde la caja que lo generó">De caja</a>
        ) : (
          <SoloLectura>
            <span className="flex gap-2 text-xs">
              {m.editable && <button type="button" onClick={() => setDrawer(m)} className="text-finance underline">Editar</button>}
              <button type="button" onClick={() => anular(m)} className="text-finance underline">Anular</button>
            </span>
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
          <ControlBancoSocio idSocio={idSocio} />
          <div className="flex flex-wrap items-center justify-between gap-4 rounded-md border border-border bg-surface p-4">
            <div>
              <h2 className="text-lg font-semibold text-ink-primary">{data.nombre}</h2>
              <p className="text-sm text-ink-secondary">
                Saldo positivo: el socio le debe a la empresa. Saldo negativo: a favor del socio.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              {data.actualizada && (
                <KpiCard
                  label="Deuda actualizada"
                  value={formatMoneda(data.actualizada.deudaActualizada)}
                  tone={data.actualizada.deudaActualizada > 0 ? "danger" : data.actualizada.deudaActualizada < 0 ? "success" : "neutral"}
                />
              )}
              {data.actualizada && data.actualizada.mutuoUSD !== 0 && (
                <KpiCard
                  label="Mutuo (solo US$)"
                  value={formatMoneda(data.actualizada.mutuoUSD, "Dolares")}
                  tone={data.actualizada.mutuoUSD > 0 ? "danger" : "success"}
                />
              )}
              <KpiCard
                label="Saldo pesos históricos"
                value={formatMoneda(data.saldo)}
                tone="neutral"
              />
              <KpiCard
                label="Saldo USD"
                value={formatMoneda(data.saldoUSD, "Dolares")}
                tone={data.saldoUSD > 0 ? "danger" : data.saldoUSD < 0 ? "success" : "neutral"}
              />
              <KpiCard
                label="Saldo Kg. Carne"
                value={`${formatCantidad(data.saldoKgCarne)} kg`}
                tone={data.saldoKgCarne > 0 ? "danger" : data.saldoKgCarne < 0 ? "success" : "neutral"}
              />
            </div>
          </div>

          {data.actualizada && (
            <p className="text-sm text-ink-secondary">
              Deuda actualizada = {formatCantidad(data.actualizada.kgCarne)} kg × índice novillo {formatMoneda(data.actualizada.novillo)} (
              {data.actualizada.fechaNovillo ? formatFecha(data.actualizada.fechaNovillo) : "—"}) ={" "}
              {formatMoneda(data.actualizada.valorKgCarne)} + {formatMoneda(data.actualizada.dolares, "Dolares")} × dólar BNA billete{" "}
              {formatMoneda(data.actualizada.dolar)} ({data.actualizada.fechaDolar ? formatFecha(data.actualizada.fechaDolar) : "—"}) ={" "}
              {formatMoneda(data.actualizada.valorDolares)}.
              {data.actualizada.mutuoUSD !== 0 &&
                ` Mutuo en dólares aparte: ${formatMoneda(data.actualizada.mutuoUSD, "Dolares")} (hoy ${formatMoneda(data.actualizada.mutuoPesos)}).`}
            </p>
          )}

          <div className="flex flex-wrap gap-3">
            <SoloLectura>
              <button type="button" onClick={() => setDrawer("asiento")} className="rounded-sm bg-agro px-4 py-2 text-sm text-white hover:opacity-90">+ Nuevo asiento</button>
              <button type="button" onClick={() => setDrawer("efectivo")} className="rounded-sm border border-border px-3 py-2 text-sm hover:bg-surface-sunken">Aporte / retiro en efectivo…</button>
            </SoloLectura>
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

          <div className="flex flex-wrap items-end gap-3 text-sm">
            <label>Buscar<input className="ml-2 rounded-sm border border-border bg-surface px-2 py-1" value={buscar} onChange={(e) => setBuscar(e.target.value)} placeholder="Concepto, proveedor…" /></label>
            <label>Año<select className="ml-2 rounded-sm border border-border bg-surface px-2 py-1" value={anio} onChange={(e) => setAnio(e.target.value)}>
              <option value="">Todos</option>
              {Array.from(new Set(data.movimientos.map((m) => m.fecha.slice(0, 4)))).sort().reverse().map((a) => <option key={a}>{a}</option>)}
            </select></label>
            <label className="flex items-center gap-2"><input type="checkbox" checked={verAnulados} onChange={(e) => setVerAnulados(e.target.checked)} /> Ver anulados</label>
          </div>
          <SideDrawer open={drawer !== null} onClose={() => setDrawer(null)} maxWidthClass={drawer === "efectivo" ? "max-w-3xl" : "max-w-lg"}
            title={drawer === "efectivo" ? `Aporte o retiro en efectivo — ${data.nombre}` : typeof drawer === "object" && drawer ? "Editar asiento" : `Nuevo asiento — ${data.nombre}`}>
            {drawer === "efectivo" ? <EfectivoSocioForm idSocio={idSocio} onListo={() => { setDrawer(null); recargar(); }} />
              : drawer !== null && <AsientoSocioForm key={typeof drawer === "object" ? drawer.idMovimiento : "nuevo"} idSocio={idSocio} movimiento={typeof drawer === "object" ? drawer : undefined} onListo={() => setDrawer(null)} />}
          </SideDrawer>
          <DataTable
            columns={columns}
            rows={[...data.movimientos].reverse().filter((m) => (verAnulados || !m.anulada) && (!anio || m.fecha.startsWith(anio))
              && (!buscar || `${m.motivo ?? ""} ${m.proveedorOrigen ?? ""} ${m.medio ?? ""}`.toLowerCase().includes(buscar.toLowerCase())))}
            keyField={(m) => m.idMovimiento}
            layout="fixed"
            stickyHeader
            rowClassName={(m) => (m.anulada ? "line-through text-ink-muted" : undefined)}
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
