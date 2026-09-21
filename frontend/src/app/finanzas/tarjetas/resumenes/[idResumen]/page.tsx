"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useState } from "react";

import {
  eliminarPagoResumen,
  fetchResumenDetalle,
  etiquetaMotivo,
  quitarEstadoLinea,
  quitarVinculoCompra,
  registrarPagoResumen,
  type LineaConsumo,
} from "@/services/tarjetasResumenesApi";
import { fetchPagosCandidatos } from "@/services/tarjetasApi";
import { urlDocumentoLocal } from "@/services/comprasApi";
import { urlParaAbrirDocumento } from "@/lib/documentoLocal";
import { PanelConciliacion } from "@/components/tarjetas-conciliacion/PanelConciliacion";
import { formatMoneda } from "@/lib/format";
import { filterInputClass } from "@/components/ui/FilterBar";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { useToast } from "@/components/ui/Toast";

function Semaforo({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
      <span
        aria-hidden
        className={`inline-block h-2.5 w-2.5 shrink-0 rounded-full ${ok ? "bg-status-success" : "bg-status-danger"}`}
      />
      <span className={ok ? "text-status-success" : "text-status-danger"}>{label}</span>
    </span>
  );
}

const CARGOS: [string, string][] = [
  ["impuestoSellos", "Impuesto de Sellos"],
  ["gastosAdmin", "Gastos de Administración"],
  ["mantCuenta", "Mantenimiento de Cuenta"],
  ["renovAnual", "Renovación Anual"],
  ["promocionBNA", "Promoción BNA"],
  ["creditoContingente", "Crédito Contingente"],
  ["intFinanc", "Interés de Financiación"],
  ["intCompens", "Interés Compensatorio"],
  ["iva105", "IVA 10,5%"],
  ["percepIVA105", "Percepción IVA 10,5%"],
  ["iva21", "IVA 21%"],
  ["percepIVA21", "Percepción IVA 21%"],
  ["percepIIBB", "Percepción IIBB"],
  ["ajusteResAnterior", "Ajuste de Resumen Anterior"],
];

function LineaConsumoRow({ linea, onChanged }: { linea: LineaConsumo; onChanged: () => void }) {
  const [panelAbierto, setPanelAbierto] = useState(false);
  const { showToast } = useToast();

  async function quitar(idVinculo: number) {
    if (linea.idLineaConsumo == null) return;
    try {
      await quitarVinculoCompra(linea.idLineaConsumo, idVinculo);
      onChanged();
    } catch {
      showToast("No se pudo quitar el vínculo.", "danger");
    }
  }

  async function volverAPendiente() {
    if (linea.idLineaConsumo == null) return;
    try {
      await quitarEstadoLinea(linea.idLineaConsumo);
      onChanged();
    } catch {
      showToast("No se pudo quitar el estado.", "danger");
    }
  }

  const resuelta = linea.estadoLinea != null;
  const conciliada = linea.comprasVinculadas.length > 0 || resuelta;
  const etiqueta =
    linea.estadoLinea === "SinDocumento"
      ? "Sin documento"
      : linea.estadoLinea === "DiferenciaAceptada"
        ? "Diferencia aceptada"
        : linea.comprasVinculadas.length > 0
          ? "Vinculada"
          : "Sin vincular";

  return (
    <tr className="border-t border-border align-top">
      <td className="py-1">{linea.fechaCompra}</td>
      <td className="py-1">{linea.detalle}</td>
      <td className="py-1 text-right font-data">{formatMoneda(linea.importe)}</td>
      <td className="py-1">
        <Semaforo ok={conciliada} label={etiqueta} />
        {linea.estadoLinea && (
          <div className="text-ink-secondary">
            {etiquetaMotivo(linea.motivoEstado ?? "")}
            {linea.detalleEstado && ` — ${linea.detalleEstado}`}
            {linea.importeDiferencia != null && ` · diferencia ${formatMoneda(linea.importeDiferencia)}`}
            {linea.estadoLinea === "SinDocumento" && (
              <button type="button" onClick={volverAPendiente} className="ml-2 text-finance underline">
                Volver a pendiente
              </button>
            )}
          </div>
        )}
        {linea.comprasVinculadas.map((v) => (
          <div key={v.idVinculo} className="flex items-center gap-1">
            <span>
              {v.proveedor ?? "—"} · {v.tipoDocumento ?? ""} {v.numeroDocumento ?? ""} — {formatMoneda(v.importeImputado)}
            </span>
            <button
              type="button"
              onClick={() => quitar(v.idVinculo)}
              className="text-ink-secondary hover:text-status-danger"
              title="Quitar vínculo"
            >
              ✕
            </button>
          </div>
        ))}
        {!conciliada && linea.idLineaConsumo != null && (
          <>
            <button type="button" onClick={() => setPanelAbierto(true)} className="mt-0.5 text-finance underline">
              Conciliar…
            </button>
            <PanelConciliacion
              idLineaConsumo={panelAbierto ? linea.idLineaConsumo : null}
              onClose={() => setPanelAbierto(false)}
              onChanged={onChanged}
            />
          </>
        )}
      </td>
    </tr>
  );
}

export default function ResumenDetallePage() {
  const params = useParams<{ idResumen: string }>();
  const idResumen = Number(params.idResumen);
  const router = useRouter();
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["tarjeta-resumen-detalle", idResumen],
    queryFn: () => fetchResumenDetalle(idResumen),
  });

  const { data: candidatos } = useQuery({
    queryKey: ["tarjeta-pagos-candidatos", data?.idTarjeta],
    queryFn: () => fetchPagosCandidatos(data!.idTarjeta),
    enabled: data != null,
  });

  function invalidar() {
    refetch();
    if (data) {
      // `refetchType: "all"` fuerza el refetch ya mismo aunque la cuenta
      // corriente de la tarjeta no esté montada en este momento — con el
      // default ("active"), React Query solo la marca vieja y espera a
      // que alguien vuelva a abrirla, y ese refetch en el remount no
      // siempre se disparaba a tiempo (el semáforo quedaba desactualizado
      // hasta un refresh manual, feedback 2026-09-21).
      queryClient.invalidateQueries({ queryKey: ["tarjeta-movimientos", data.idTarjeta], refetchType: "all" });
      queryClient.invalidateQueries({ queryKey: ["tarjeta-pagos-candidatos", data.idTarjeta], refetchType: "all" });
    }
  }

  async function vincularPago(candidato: { origen: string; idMovimiento: number; fecha: string; importe: number }) {
    try {
      await registrarPagoResumen(idResumen, {
        fecha: candidato.fecha,
        importe: candidato.importe,
        origen: candidato.origen,
        idMovimientoOrigen: candidato.idMovimiento,
      });
      showToast("Pago vinculado.", "success");
      invalidar();
    } catch {
      showToast("No se pudo vincular el pago.", "danger");
    }
  }

  async function eliminarPago(idPago: number) {
    try {
      await eliminarPagoResumen(idResumen, idPago);
      invalidar();
    } catch {
      showToast("No se pudo eliminar el pago.", "danger");
    }
  }

  // Tolerancia $0.10 fija (no proporcional): la fórmula suma 14 cargos +
  // N líneas, cada uno redondeado por separado en su origen — el ruido
  // depende de CUÁNTOS términos se suman, no de cuánto suman. Medido
  // contra los 293 resúmenes reales: máximo real observado $0.03, sin
  // ningún caso entre $0.05 y $0.50 (análisis del especialista
  // financiero, feedback 2026-09-21). El monto de la diferencia no se
  // muestra en la UI (feedback 2026-09-21: "es solo ruido para el
  // usuario") — el semáforo es binario, Conciliado o Falta conciliar.
  const TOLERANCIA_CONCILIACION = 0.1;
  const totalPagado = data?.pagos.reduce((acc, p) => acc + p.importe, 0) ?? 0;
  const diferenciaRedondeo = data ? Math.round((data.totalCalculado - totalPagado) * 100) / 100 : 0;
  const conciliado = data != null && diferenciaRedondeo <= TOLERANCIA_CONCILIACION;
  const estadoLabel = conciliado ? "Pago conciliado" : "Falta conciliar el pago";

  return (
    <main className="mx-auto max-w-none px-8 py-3">
      <button type="button" onClick={() => router.back()} className="text-sm text-finance underline">
        ← Volver
      </button>

      {isLoading && <LoadingState />}
      {isError && <ErrorState message="Ocurrió un error al cargar el resumen." onRetry={() => refetch()} />}

      {data && (
        <div className="mt-2 space-y-3">
          <div className="flex items-center justify-between">
            <h1 className="text-base font-semibold">
              Resumen {data.codigo} — {data.tarjeta}
            </h1>
            <div className="flex items-center gap-3">
              <Semaforo ok={conciliado} label={estadoLabel} />
              <Link href={`/finanzas/tarjetas/resumenes/${idResumen}/editar`} className="text-sm text-finance underline">
                Editar
              </Link>
            </div>
          </div>
          <p className="text-xs text-ink-secondary">
            Cierre: {data.fechaCierre} · Vencimiento: {data.fechaVencimiento}
          </p>
          {data.urlResumenOriginal && (
            <p className="text-xs">
              <a
                href={urlParaAbrirDocumento(data.urlResumenOriginal, "", urlDocumentoLocal)}
                target="_blank"
                rel="noreferrer"
                className="text-finance underline"
              >
                Ver resumen original (PDF)
              </a>
            </p>
          )}

          <div className="rounded-md border border-border bg-surface p-2">
            <h2 className="text-xs font-medium text-ink-secondary">Cargos e impuestos</h2>
            <dl className="mt-1 grid grid-cols-[repeat(auto-fit,minmax(11rem,1fr))] gap-x-4 gap-y-1 text-xs">
              {CARGOS.map(([key, label]) => {
                const value = (data as unknown as Record<string, number>)[key] ?? 0;
                if (!value) return null;
                return (
                  <div key={key} className="flex justify-between gap-2">
                    <dt className="text-ink-secondary">{label}</dt>
                    <dd className="font-data">{formatMoneda(value)}</dd>
                  </div>
                );
              })}
            </dl>
            <p className="mt-2 font-data text-sm font-semibold text-ink-primary">
              Total calculado: {formatMoneda(data.totalCalculado)}
            </p>
          </div>

          <div className="rounded-md border border-border bg-surface p-2">
            <h2 className="text-xs font-medium text-ink-secondary">
              Líneas de consumo {data.lineas.length === 0 && "(ninguna — solo cabecera)"}
            </h2>
            {data.lineas.length > 0 && (
              <table className="mt-1 w-full text-xs">
                <thead>
                  <tr className="text-left text-ink-secondary">
                    <th className="py-1">Fecha</th>
                    <th className="py-1">Detalle</th>
                    <th className="py-1 text-right">Importe</th>
                    <th className="py-1">Facturas vinculadas</th>
                  </tr>
                </thead>
                <tbody>
                  {data.lineas.map((l) => (
                    <LineaConsumoRow key={l.idLineaConsumo} linea={l} onChanged={invalidar} />
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="rounded-md border border-border bg-surface p-2">
            <h2 className="text-xs font-medium text-ink-secondary">Pagos registrados</h2>
            {data.pagos.length === 0 && <p className="mt-1 text-xs text-ink-secondary">Ningún pago registrado todavía.</p>}
            {data.pagos.length > 0 && (
              <table className="mt-1 w-full text-xs">
                <tbody>
                  {data.pagos.map((p) => (
                    <tr key={p.idPago} className="border-t border-border">
                      <td className="py-1">{p.fecha}</td>
                      <td className="py-1 text-right font-data">{formatMoneda(p.importe)}</td>
                      <td className="py-1 text-ink-secondary">{p.origen ?? "Manual"}</td>
                      <td className="py-1 text-right">
                        <button
                          type="button"
                          onClick={() => eliminarPago(p.idPago)}
                          className="text-ink-secondary hover:text-status-danger"
                        >
                          ✕
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {!conciliado && candidatos && candidatos.length > 0 && (
              <div className="mt-2">
                <h3 className="text-xs text-ink-secondary">
                  Movimientos bancarios candidatos (misma tarjeta, no vinculados todavía)
                </h3>
                <ul className="mt-1 space-y-1">
                  {candidatos.map((c) => (
                    <li key={`${c.origen}-${c.idMovimiento}`} className="flex items-center justify-between gap-2 text-xs">
                      <span>
                        {c.fecha} · {formatMoneda(c.importe)} · {c.concepto ?? c.origen}
                      </span>
                      <button
                        type="button"
                        onClick={() => vincularPago(c)}
                        className="rounded-sm border border-border px-2 py-0.5 text-ink-secondary hover:text-ink-primary"
                      >
                        Vincular como pago de este resumen
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </main>
  );
}
