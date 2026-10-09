"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { formatFecha, formatMoneda } from "@/lib/format";
import {
  revisionCuentasApi,
  type EstadoMarca,
  type FuenteRespaldo,
  type PagoSinFactura,
} from "@/services/revisionCuentasApi";

const NOMBRE_ESTADO: Record<EstadoMarca, string> = {
  pendiente: "Pendiente",
  "factura-cargada": "Factura cargada",
  "sin-documento": "Sin documento",
  anticipo: "Anticipo",
};

const NOMBRE_MEDIO: Record<string, string> = {
  bna: "Banco Nación",
  galicia: "Galicia",
  efectivo: "Efectivo",
  tarjetas: "Tarjeta",
  retencion: "Retención",
  valores: "Valores",
  "venta-granos": "Venta de granos",
};

const rotulo = (medio: string) => NOMBRE_MEDIO[medio] ?? medio;
const claveDe = (p: PagoSinFactura) => `${p.medio}/${p.idMovimiento}`;

/** Fila de un pago sin factura con sus acciones de marca (las acciones se ocultan para el rol de solo lectura). */
function FilaPago({ idContacto, pago, alMarcar }: { idContacto: number; pago: PagoSinFactura; alMarcar: () => void }) {
  const [abierta, setAbierta] = useState(false);
  const [estado, setEstado] = useState<EstadoMarca>("sin-documento");
  const [nota, setNota] = useState("");
  const [fuente, setFuente] = useState<FuenteRespaldo | "">("");
  const [error, setError] = useState<string | null>(null);
  const marcar = useMutation({
    mutationFn: () =>
      revisionCuentasApi.marcarPagoSinFactura(idContacto, pago.medio, pago.idMovimiento, {
        estado,
        nota: nota.trim() || null,
        fuenteRespaldo: estado === "factura-cargada" && fuente ? fuente : null,
      }),
    onSuccess: () => { setAbierta(false); setError(null); alMarcar(); },
    onError: (e) => setError(e instanceof Error ? e.message : "No se pudo guardar la marca."),
  });
  const marca = pago.marca;
  return (
    <li className="rounded border border-line p-2">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="font-medium">{formatFecha(pago.fecha)}</span>
        <span>{rotulo(pago.medio)} #{pago.idMovimiento}</span>
        <b>{formatMoneda(pago.importe)}</b>
        {pago.retencionAsociada ? <span className="text-ink-secondary">+ retención {formatMoneda(pago.retencionAsociada)}</span> : null}
        <span className="text-ink-secondary">
          Factura esperada: <b>{formatMoneda(pago.importeEsperadoFactura)}</b>, entre el {formatFecha(pago.fechaEsperadaDesde)} y el {formatFecha(pago.fechaEsperadaHasta)}
        </span>
        {pago.confianza === "media" && <span className="text-status-warning">Se cubrió en parte con facturas viejas</span>}
        {marca && marca.estado !== "pendiente" && (
          <span className="rounded bg-surface-muted px-1.5">{NOMBRE_ESTADO[marca.estado]}{marca.nota ? `: ${marca.nota}` : ""}</span>
        )}
      </div>
      <SoloLectura>
        {!abierta ? (
          <button type="button" onClick={() => setAbierta(true)} className="mt-1 rounded border border-line px-2 py-0.5">Marcar</button>
        ) : (
          <div className="mt-2 space-y-2">
            <label className="block">
              Qué pasó con este pago{" "}
              <select value={estado} onChange={(e) => setEstado(e.target.value as EstadoMarca)} className="rounded border border-line px-1 py-0.5">
                <option value="factura-cargada">Ya cargué la factura</option>
                <option value="sin-documento">No hay documento (decisión mía)</option>
                <option value="anticipo">Es un anticipo</option>
                <option value="pendiente">Dejarlo pendiente</option>
              </select>
            </label>
            {estado === "factura-cargada" && (
              <label className="block">
                La factura no tiene archivo: ¿en qué se respalda?{" "}
                <select value={fuente} onChange={(e) => setFuente(e.target.value as FuenteRespaldo | "")} className="rounded border border-line px-1 py-0.5">
                  <option value="">Tiene archivo</option>
                  <option value="portal">Portal del proveedor</option>
                  <option value="estado-de-cuenta">Estado de cuenta</option>
                  <option value="pdf">PDF</option>
                </select>
              </label>
            )}
            <label className="block">
              Nota{estado === "sin-documento" ? " (obligatoria)" : ""}{" "}
              <input value={nota} onChange={(e) => setNota(e.target.value)} maxLength={500} className="w-full rounded border border-line px-1 py-0.5" />
            </label>
            {error && <p role="alert" className="text-status-danger">{error}</p>}
            <div className="flex gap-2">
              <button type="button" disabled={marcar.isPending} onClick={() => marcar.mutate()} className="rounded bg-finance px-3 py-1 text-white">
                {marcar.isPending ? "Guardando…" : "Guardar marca"}
              </button>
              <button type="button" onClick={() => setAbierta(false)} className="rounded border border-line px-2 py-0.5">Cancelar</button>
            </div>
          </div>
        )}
      </SoloLectura>
    </li>
  );
}

/**
 * Pagos de la cuenta que no tienen una factura que los respalde (detector de la 036): para cada uno, la factura que
 * debería existir (importe y fechas esperadas). Lo anterior a 2021 se muestra aparte y no bloquea el cierre.
 */
export function PagosSinFactura({ idContacto }: { idContacto: number }) {
  const qc = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["revision-pagos-sin-factura", idContacto],
    queryFn: () => revisionCuentasApi.pagosSinFactura(idContacto),
  });
  const refrescar = () => {
    for (const k of ["revision-pagos-sin-factura", "revision-ficha"]) qc.invalidateQueries({ queryKey: [k] });
  };

  if (isLoading) return <p className="text-xs text-ink-secondary">Buscando pagos sin factura…</p>;
  if (error || !data || !Array.isArray(data.pagos)) return <p role="alert" className="text-xs text-status-danger">No se pudieron calcular los pagos sin factura.</p>;

  const recientes = data.pagos.filter((p) => !p.anteriorA2021);
  const viejos = data.pagos.filter((p) => p.anteriorA2021);
  const pendientes = recientes.filter((p) => !p.marca || p.marca.estado === "pendiente");

  return (
    <section className="rounded border border-line p-3 text-xs">
      <h2 className="text-sm font-semibold">Pagos sin factura</h2>
      <p className="text-ink-secondary">
        Pagos que no tienen una factura cargada que los respalde. Con esta pista se busca el documento y se marca cada caso.
      </p>
      {!data.consistencia.cierra && (
        <p role="alert" className="mt-1 text-status-warning">
          El detector no cierra con el saldo de la cuenta (diferencia a revisar): no confíes en esta lista hasta explicarla.
        </p>
      )}
      {data.consistencia.sinApertura && (
        <p className="mt-1 text-ink-secondary">Esta cuenta arranca antes de 2011: se informa sin apertura.</p>
      )}
      {recientes.length === 0 ? (
        <p className="mt-2 text-status-success">No hay pagos sin factura desde 2021.</p>
      ) : (
        <>
          <p className="mt-2">
            <b>{pendientes.length}</b> pendientes de {recientes.length} desde 2021.
          </p>
          <ul className="mt-1 space-y-1">
            {recientes.map((p) => <FilaPago key={claveDe(p)} idContacto={idContacto} pago={p} alMarcar={refrescar} />)}
          </ul>
        </>
      )}
      {data.facturasSinPago.length > 0 && (
        <p className="mt-2 text-ink-secondary">
          Facturas sin pago: {data.facturasSinPago.length} por {formatMoneda(data.facturasSinPago.reduce((s, f) => s + f.importe, 0))}.
        </p>
      )}
      {viejos.length > 0 && (
        <details className="mt-2">
          <summary className="cursor-pointer">Anteriores a 2021 ({viejos.length}): no bloquean el cierre si el saldo cierra</summary>
          <ul className="mt-1 space-y-1">
            {viejos.map((p) => <FilaPago key={claveDe(p)} idContacto={idContacto} pago={p} alMarcar={refrescar} />)}
          </ul>
        </details>
      )}
    </section>
  );
}
