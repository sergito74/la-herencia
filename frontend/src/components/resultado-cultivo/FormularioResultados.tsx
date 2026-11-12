"use client";

import { useQuery } from "@tanstack/react-query";

import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatCantidad, formatFecha, formatNumero } from "@/lib/format";
import { fetchFormularioResultados, type ParMonto } from "@/services/resultadoCultivoApi";

import { ar, celdaNum, Dato, TablaCostosDirectos, Titulo, us } from "./FormularioAccess";

const pct = (v: number | undefined) => (v == null ? "—" : `${formatNumero(v * 100, { min: 2, max: 2 })} %`);
const kg = (v: number | undefined) => (v == null ? "—" : `${formatNumero(v, { max: 0 })} kg`);

function Bloque({ titulo, children, className = "" }: { titulo?: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={`rounded-md border border-border bg-surface ${className}`}>
      {titulo && <h3 className="border-b border-border bg-surface-sunken px-3 py-1.5 text-sm font-semibold">{titulo}</h3>}
      {children}
    </section>
  );
}

function FilaMonto({ label, m, fuerte, signo = "" }: { label: string; m: ParMonto | undefined; fuerte?: boolean; signo?: string }) {
  return (
    <tr className={`border-b border-border ${fuerte ? "bg-surface-sunken font-semibold" : ""}`}>
      <td className="px-2 py-1">{signo && <span className="mr-1 text-ink-muted">{signo}</span>}{label}</td>
      <td className={celdaNum}>{ar(m?.pesos)}</td>
      <td className={celdaNum}>{us(m?.dolares)}</td>
    </tr>
  );
}

/** Resultado de un cultivo con el diseño y los cálculos del formulario FrmResultados de Access. */
export function FormularioResultados({ idCultivo, idCampania }: { idCultivo: number; idCampania: number }) {
  const { data: d, isLoading, isError, refetch } = useQuery({
    queryKey: ["access-resultados", idCultivo, idCampania],
    queryFn: () => fetchFormularioResultados(idCultivo, idCampania),
  });
  if (isLoading) return <LoadingState />;
  if (isError || !d) return <ErrorState message="No se pudo calcular el resultado." onRetry={refetch} />;
  if (d.aviso) return <p className="text-sm text-status-warning">{d.aviso}</p>;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-x-8 gap-y-1 rounded-md border border-border bg-surface px-3 py-2 text-sm">
        <Titulo cultivo={d.cultivo} campania={d.campania} />
        <Dato label="Inicio">{formatFecha(d.fechaInicio ?? null)}</Dato>
        <Dato label="Fin">{formatFecha(d.fechaFin ?? null)}</Dato>
        <Dato label="Ocupación lote (días)">{d.ocupacionDias ?? "Indefinido"}</Dato>
      </div>

      {/* Indicadores: superficies, cantidades, rindes, margen y rentabilidad (fila superior de Access). */}
      <div className="grid gap-3 lg:grid-cols-[1fr_1fr_1fr_1.1fr_1.1fr]">
        <Bloque className="px-3 py-2 text-sm">
          <Dato label="Superficie afectada">{formatCantidad(d.superficieAfectada ?? 0)} ha</Dato>
          <Dato label="Superficie sembrada">{formatCantidad(d.superficieSembrada ?? 0)} ha{d.superficieSembradaTeorica && <span className="ml-1 text-xs font-normal text-status-warning" title="Sin factura de siembra: es la superficie planificada">(teórica)</span>}</Dato>
          <Dato label="Superficie cosechada">{formatCantidad(d.superficieCosechada ?? 0)} ha</Dato>
          <Dato label="Superficie picada">{formatCantidad(d.superficiePicada ?? 0)} ha</Dato>
        </Bloque>
        <Bloque className="px-3 py-2 text-sm">
          <Dato label="Cantidad cosechada">{kg(d.cantidadCosechada)}</Dato>
          <Dato label="Cantidad vendida">{kg(d.cantidadVendida)}</Dato>
          <Dato label="Cantidad consumida">{kg(d.cantidadConsumida)}</Dato>
        </Bloque>
        <Bloque className="px-3 py-2 text-sm">
          <Dato label="Rinde">{kg(d.rinde)}/ha</Dato>
          <Dato label="Rinde indiferencia">{kg(d.rindeIndiferencia)}/ha</Dato>
          <Dato label="Vol. indiferencia">{kg(d.volumenIndiferencia)}</Dato>
        </Bloque>
        <Bloque>
          <table className="w-full text-sm">
            <thead className="text-xs text-ink-secondary"><tr><th /><th className="px-2 py-1 text-right font-medium">AR$</th><th className="px-2 py-1 text-right font-medium">US$</th></tr></thead>
            <tbody>
              <tr><td className="px-2 py-1 font-medium">Margen Bruto</td><td className={celdaNum}>{ar(d.margenBruto?.pesos)}</td><td className={celdaNum}>{us(d.margenBruto?.dolares)}</td></tr>
              <tr><td className="px-2 py-1 font-medium">MB / HA</td><td className={celdaNum}>{ar(d.margenBrutoHa?.pesos)}</td><td className={celdaNum}>{us(d.margenBrutoHa?.dolares)}</td></tr>
            </tbody>
          </table>
        </Bloque>
        <Bloque>
          <table className="w-full text-sm">
            <thead className="text-xs text-ink-secondary"><tr><th /><th className="px-2 py-1 text-right font-medium">AR$</th><th className="px-2 py-1 text-right font-medium">US$</th></tr></thead>
            <tbody>
              <tr><td className="px-2 py-1 font-medium">Rentabilidad</td><td className={celdaNum}>{pct(d.rentabilidad?.pesos)}</td><td className={celdaNum}>{pct(d.rentabilidad?.dolares)}</td></tr>
              <tr><td className="px-2 py-1 font-medium">Renta anual</td><td className={celdaNum}>{pct(d.rentaAnual?.pesos)}</td><td className={celdaNum}>{pct(d.rentaAnual?.dolares)}</td></tr>
            </tbody>
          </table>
        </Bloque>
      </div>

      <div className="grid gap-3 xl:grid-cols-2">
        <TablaCostosDirectos filas={d.costosDirectos ?? []} totales={[
          { label: "Costos Implantación", monto: d.implantacion },
          { label: "Costo Implantación Silo", monto: d.silo, sinHa: true },
          { label: "Costos Cosecha", monto: d.cosecha },
          { label: "Totales Costos Cultivo Agrícola", monto: d.totalCostos, fuerte: true },
        ]} />

        <Bloque titulo="Ventas">
          <p className="flex justify-end gap-2 border-b border-border px-3 py-1 text-sm">
            <span className="text-ink-secondary">Precio Neto (Tn)</span><strong className="tabular-nums">{us(d.precioNetoTn)}</strong>
          </p>
          <table className="w-full text-sm">
            <thead className="text-xs text-ink-secondary">
              <tr className="border-b border-border"><th /><th className="px-2 py-1 text-right font-medium">AR$</th><th className="px-2 py-1 text-right font-medium">US$</th></tr>
            </thead>
            <tbody>
              <FilaMonto label="Venta Bruta" m={d.ventaBruta} />
              <FilaMonto label="Bonificaciones y Ajustes" m={d.bonificaciones} />
              <FilaMonto label="Total Ventas" m={d.totalVentas} fuerte />
              <tr><td colSpan={3} className="bg-surface-sunken px-2 py-1 text-xs font-semibold text-ink-secondary">Deducciones y Gastos Liquidaciones</td></tr>
              {(d.deducciones ?? []).map((x) => (
                <tr key={x.detalle} className="border-b border-border text-ink-secondary">
                  <td className="py-0.5 pl-5 pr-2">{x.detalle}</td><td className={celdaNum}>{ar(x.pesos)}</td><td className={celdaNum}>{us(x.dolares)}</td>
                </tr>
              ))}
              <tr><td colSpan={3} className="bg-surface-sunken px-2 py-1 text-xs font-semibold text-ink-secondary">Gastos</td></tr>
              {(d.gastos ?? []).map((x) => (
                <tr key={x.concepto} className="border-b border-border text-ink-secondary">
                  <td className="py-0.5 pl-5 pr-2">{x.concepto}</td><td className={celdaNum}>{ar(x.pesos)}</td><td className={celdaNum}>{us(x.dolares)}</td>
                </tr>
              ))}
              {!d.gastos?.length && <tr><td colSpan={3} className="py-0.5 pl-5 text-ink-muted">—</td></tr>}
              <FilaMonto label="Total Deducciones y gastos" m={d.totalDeducciones} signo="−" />
              <FilaMonto label="Recupero por seguro" m={d.recuperoSeguro} signo="+" />
              <FilaMonto label="Producción No comercializada" m={d.produccionNoComercializada} signo="+" />
              <FilaMonto label="Total Venta Neta" m={d.totalVentaNeta} fuerte />
            </tbody>
          </table>
        </Bloque>
      </div>
    </div>
  );
}
