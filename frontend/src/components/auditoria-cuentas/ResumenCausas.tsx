"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatFecha, formatMoneda } from "@/lib/format";
import { fetchResumenAuditoria, type CausaCuenta } from "@/services/auditoriaCuentasApi";

import { GrupoExcepciones } from "./GrupoExcepciones";
import { ParametrosAuditoria } from "./ParametrosAuditoria";
import { EmpezarRevision } from "./EmpezarRevision";
import { FifoTandas } from "./FifoTandas";
import { ReglasConocidas } from "./ReglasConocidas";

export const NOMBRES_CAUSA: Record<CausaCuenta, string> = {
  coincide: "Coincide con el Access",
  "coincide-causa-conocida": "Coincide con causa conocida (diferencia explicada)",
  "diferencia-menor-umbral": "Diferencia menor al umbral",
  "fuera-de-plazo-decidido": "Fuera de plazo, decidido a mano o por FIFO",
  "aplicacion-fuera-de-plazo": "Pagos aplicados fuera de plazo",
  "doble-descuento-tarjeta": "Posible doble descuento con tarjeta",
  "nota-sin-imputar": "Nota sin imputar",
  "impuesto-sin-boleta": "Impuesto sin boleta",
  "movimiento-sin-contacto": "Movimiento sin contacto",
  sobrepago: "Pago de más",
  "contacto-duplicado": "Contacto duplicado",
  "falta-documento": "Falta un documento",
  "sin-referencia": "Sin referencia en el Access",
  otros: "Otros: diferencia sin explicar",
};

/** Estado de todas las cuentas contra el Access al corte, agrupado por causa (035, FR-001/FR-003). */
export function ResumenCausas() {
  const [abierto, setAbierto] = useState<CausaCuenta | null>(null);
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["auditoria-resumen"], queryFn: fetchResumenAuditoria });
  if (isLoading) return <LoadingState />;
  if (isError || !data) return <ErrorState message="No se pudo cargar la auditoría." onRetry={() => refetch()} />;

  const excepciones = data.causas.filter((g) => g.excepcion && !g.adicional);
  const imputaciones = data.causas.filter((g) => g.adicional);
  const resto = data.causas.filter((g) => !g.excepcion && !g.adicional);
  const fila = (g: (typeof data.causas)[number]) => (
    <li key={g.causa}>
      <button type="button" onClick={() => setAbierto(abierto === g.causa ? null : g.causa)} className="flex w-full justify-between gap-3 py-1 text-left text-sm">
        <span className="underline">{NOMBRES_CAUSA[g.causa] ?? g.causa}</span>
        <span>
          {g.movimientos ? <><b>{g.movimientos}</b> movimientos</> : <><b>{g.cuentas}</b> cuentas</>} · {formatMoneda(g.importe)}
        </span>
      </button>
      {abierto === g.causa && (
        <div className="mb-3 rounded border border-line p-3">
          <GrupoExcepciones causa={g.causa} titulo={NOMBRES_CAUSA[g.causa] ?? g.causa} />
        </div>
      )}
    </li>
  );

  return (
    <div className="space-y-4">
      <p className="text-sm">
        De <b>{data.totalCuentas}</b> cuentas, <b>{data.coinciden}</b> coinciden con el Access y <b>{data.conDiferencia}</b> tienen una diferencia por revisar.
      </p>
      <p className="text-xs text-ink-secondary">
        Corte: {formatFecha(data.fechaCorte)}. {data.avisoCorte} Umbral: {formatMoneda(data.parametros.umbralPesos)} (solo en pesos; en dólares no hay umbral).
      </p>
      <section>
        <h2 className="text-sm font-semibold">Para revisar</h2>
        {excepciones.length === 0 ? <p className="text-xs text-status-success">No hay excepciones.</p> : <ul className="divide-y divide-line">{excepciones.map(fila)}</ul>}
      </section>
      <section>
        <h2 className="text-sm font-semibold">Imputaciones sospechosas</h2>
        <p className="text-xs text-ink-secondary">No cambian el saldo: avisan que un pago quedó aplicado a facturas que no corresponden. Una cuenta puede figurar acá aunque su saldo coincida.</p>
        {imputaciones.length === 0 ? <p className="text-xs text-status-success">No hay.</p> : <ul className="divide-y divide-line">{imputaciones.map(fila)}</ul>}
      </section>
      <section>
        <h2 className="text-sm font-semibold">Ya explicadas (no cuentan como excepción)</h2>
        <ul className="divide-y divide-line">{resto.map(fila)}</ul>
      </section>
      <EmpezarRevision />
      <FifoTandas />
      <ReglasConocidas />
      <ParametrosAuditoria parametros={data.parametros} />
    </div>
  );
}
