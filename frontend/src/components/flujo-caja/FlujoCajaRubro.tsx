"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { AplicarPagoPanel } from "@/components/aplicaciones-pago/AplicarPagoPanel";
import { FilterBar, FilterField, filterInputClass } from "@/components/ui/FilterBar";
import { SideDrawer } from "@/components/ui/SideDrawer";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatFecha, formatMoneda } from "@/lib/format";
import {
  fetchDetalleRubro,
  fetchPorRubro,
  urlExportarPorRubro,
  type FilaRubro,
  type FlujoPorRubro,
  type GranularidadRubro,
  type MonedaRubro,
  type SeccionRubro,
} from "@/services/flujoCajaApi";

// 031: desde dónde se vinculó el documento.
const VIAS: Record<string, string> = {
  aplicacion: "Aplicación",
  tarjeta: "Tarjeta",
  "valor-propio": "Cheque",
  tesoreria: "Tesorería",
  "backfill-impuesto": "Impuesto",
};

const SIN_APLICAR = new Set(["Pendiente de aplicar", "Histórico sin aplicar"]);
const GRANULARIDADES: { valor: GranularidadRubro; etiqueta: string }[] = [
  { valor: "semanal", etiqueta: "Semana" },
  { valor: "mensual", etiqueta: "Mes" },
  { valor: "trimestral", etiqueta: "Trimestre" },
  { valor: "anual", etiqueta: "Año" },
];

function rangoPorDefecto(): { desde: string; hasta: string } {
  const hoy = new Date();
  const desde = new Date(hoy.getFullYear(), hoy.getMonth() - 11, 1);
  const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  return { desde: iso(desde), hasta: iso(hoy) };
}

type Celda = { periodo: string; seccion: SeccionRubro; rubro: string; centroCosto?: string | null };

/** Flujo de caja real por rubro (030): formato de la hoja "Cash Flow 1" de Sergio. */
export function FlujoCajaRubro() {
  const def = rangoPorDefecto();
  const [desde, setDesde] = useState(def.desde);
  const [hasta, setHasta] = useState(def.hasta);
  const [aplicado, setAplicado] = useState(def);
  const [granularidad, setGranularidad] = useState<GranularidadRubro>("mensual");
  const [moneda, setMoneda] = useState<MonedaRubro>("ARS");
  const [celda, setCelda] = useState<Celda | null>(null);
  const [aplicando, setAplicando] = useState<{ origenMovimiento: string; idMovimientoOrigen: number } | null>(null);

  const params = { fechaDesde: aplicado.desde, fechaHasta: aplicado.hasta, granularidad, moneda };
  const q = useQuery({ queryKey: ["flujo-por-rubro", params], queryFn: () => fetchPorRubro(params) });
  const detalle = useQuery({
    queryKey: ["flujo-por-rubro-detalle", params, celda],
    queryFn: () => fetchDetalleRubro({ ...params, ...celda! }),
    enabled: celda !== null,
  });

  const fmt = (v: number | null | undefined) =>
    v == null ? "—" : formatMoneda(v, moneda === "USD" ? "Dolares" : "Pesos");

  return (
    <div className="space-y-4">
      <FilterBar
        onSubmit={(e) => {
          e.preventDefault();
          setAplicado({ desde, hasta });
          setCelda(null);
        }}
      >
        <FilterField label="Desde">
          <input type="date" className={filterInputClass} value={desde} onChange={(e) => setDesde(e.target.value)} />
        </FilterField>
        <FilterField label="Hasta">
          <input type="date" className={filterInputClass} value={hasta} onChange={(e) => setHasta(e.target.value)} />
        </FilterField>
        <button type="submit" className="rounded bg-finance px-3 py-2 text-sm text-white">
          Aplicar rango
        </button>
      </FilterBar>

      <div className="flex flex-wrap items-center gap-4">
        <Segmentado
          opciones={GRANULARIDADES}
          valor={granularidad}
          onChange={(g) => {
            setGranularidad(g);
            setCelda(null);
          }}
        />
        <Segmentado
          opciones={[
            { valor: "ARS", etiqueta: "Pesos" },
            { valor: "USD", etiqueta: "Dólares" },
          ]}
          valor={moneda}
          onChange={(m) => {
            setMoneda(m);
            setCelda(null);
          }}
        />
        <a
          href={urlExportarPorRubro(params)}
          className="ml-auto rounded border border-border px-3 py-1.5 text-sm hover:bg-surface-sunken"
        >
          Exportar a Excel
        </a>
      </div>

      {q.isLoading && <LoadingState rows={8} />}
      {q.isError && <ErrorState message="No se pudo calcular el flujo de caja por rubro." onRetry={() => q.refetch()} />}
      {q.data && (
        <>
          <Avisos data={q.data} fmt={fmt} />
          <TablaRubros data={q.data} fmt={fmt} onCelda={setCelda} />
        </>
      )}

      <SideDrawer
        open={celda !== null}
        onClose={() => setCelda(null)}
        title={celda ? `${celda.rubro}${celda.centroCosto ? ` · ${celda.centroCosto}` : ""} — ${celda.periodo}` : ""}
      >
        {detalle.isLoading && <p className="px-4 py-3 text-sm text-ink-secondary">Cargando…</p>}
        {detalle.data && (
          <div>
            <p className="px-4 py-2 text-sm font-medium">
              Total {fmt(detalle.data.total)} · {detalle.data.items.length} movimientos
            </p>
            <ul className="divide-y divide-border">
              {detalle.data.items.map((p, i) => (
                <li key={i} className="px-4 py-2.5 text-sm">
                  {/* Fila superior: Fecha, Medio/Cuenta e Importe */}
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-ink">
                      {formatFecha(p.fecha)} · {p.cuenta}
                    </span>
                    <span className={`font-semibold ${p.importeArs < 0 ? "text-status-danger" : "text-agro"}`}>
                      {moneda === "USD" ? fmt(p.importeUsd) : fmt(p.importeArs)}
                    </span>
                  </div>

                  {/* Tarjeta de Comprobante / Concepto Legible */}
                  {p.documentoDetalle ? (
                    <div className="mt-1.5 rounded-md border border-border/80 bg-surface/90 px-3 py-2 text-xs shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
                      <div className="flex items-baseline justify-between gap-2">
                        <span className="font-semibold text-ink">
                          {p.documentoDetalle.proveedor || p.contacto || "Comprobante"}
                        </span>
                        <span className="font-medium text-ink-secondary">
                          {p.documentoDetalle.tipoComprobante} {p.documentoDetalle.nroComprobante ? `N° ${p.documentoDetalle.nroComprobante}` : ""}
                        </span>
                      </div>
                      {p.documentoDetalle.detalleConcepto && (
                        <div className="mt-1 text-ink-secondary leading-snug">
                          {p.documentoDetalle.detalleConcepto}
                        </div>
                      )}
                      <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 border-t border-border/50 pt-1 text-[11px] text-ink-tertiary">
                        <span>Origen bancario: {p.concepto || "—"}</span>
                        {p.documentoAplicado?.via && (
                          <span>· vía {VIAS[p.documentoAplicado.via] ?? p.documentoAplicado.via}</span>
                        )}
                        {p.importeArs !== p.importeMovimiento && (
                          <span>· Parte de un movimiento de {formatMoneda(p.importeMovimiento)}</span>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="mt-1 text-xs text-ink-secondary">
                      <div className="flex items-baseline justify-between gap-2 font-medium text-ink">
                        <span>{p.contacto || p.concepto || "—"}</span>
                        {p.documentoAplicado ? (
                          <span className="text-[11px] text-ink-tertiary">
                            {VIAS[p.documentoAplicado.via] ? `vía ${VIAS[p.documentoAplicado.via]}` : ""}
                          </span>
                        ) : (
                          <span className="rounded bg-status-warning-bg/40 px-1.5 py-0.5 text-[10px] text-status-warning font-medium">
                            Sin comprobante aplicado
                          </span>
                        )}
                      </div>
                      {p.contacto && p.concepto && (
                        <p className="mt-0.5 text-[11px] text-ink-tertiary">Banco: {p.concepto}</p>
                      )}
                      {p.importeArs !== p.importeMovimiento && (
                        <p className="mt-0.5 text-[11px] text-ink-tertiary">
                          Parte de un movimiento de {formatMoneda(p.importeMovimiento)}
                        </p>
                      )}
                    </div>
                  )}

                  {moneda === "USD" && (
                    <p className="mt-1 text-[11px] text-ink-secondary">
                      {p.cotizacion
                        ? `Cotización ${formatMoneda(p.cotizacion)} del ${formatFecha(p.fechaCotizacion)}`
                        : "Sin tipo de cambio: no suma en dólares"}
                    </p>
                  )}
                  {SIN_APLICAR.has(p.rubro) && p.origenMovimiento && p.idMovimiento != null && (
                    <button
                      type="button"
                      className="mt-1.5 text-xs font-medium text-agro underline hover:text-agro-hover"
                      onClick={() => setAplicando({ origenMovimiento: p.origenMovimiento!, idMovimientoOrigen: p.idMovimiento! })}
                    >
                      Aplicar a factura/venta…
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </SideDrawer>

      <SideDrawer open={aplicando !== null} onClose={() => setAplicando(null)} title="Aplicar pago/cobro">
        {aplicando && (
          <div className="p-4">
            <AplicarPagoPanel
              origenMovimiento={aplicando.origenMovimiento}
              idMovimientoOrigen={aplicando.idMovimientoOrigen}
              onAplicado={() => {
                setAplicando(null);
                q.refetch();
                detalle.refetch();
              }}
            />
          </div>
        )}
      </SideDrawer>
    </div>
  );
}

function Segmentado<T extends string>({
  opciones,
  valor,
  onChange,
}: {
  opciones: { valor: T; etiqueta: string }[];
  valor: T;
  onChange: (v: T) => void;
}) {
  return (
    <div className="inline-flex rounded-md border border-border">
      {opciones.map((o) => (
        <button
          key={o.valor}
          type="button"
          onClick={() => onChange(o.valor)}
          className={`px-3 py-1 text-sm ${valor === o.valor ? "bg-finance-light text-finance" : "text-ink-secondary"}`}
        >
          {o.etiqueta}
        </button>
      ))}
    </div>
  );
}

function Avisos({ data }: { data: FlujoPorRubro; fmt: (v: number | null) => string }) {
  const sinTc = data.sinTipoCambio.reduce((a, s) => a + s.cantidad, 0);
  if (data.moneda !== "USD" || (sinTc === 0 && data.saldosSinTipoCambio.length === 0)) {
    return null;
  }
  return (
    <div className="space-y-2 text-sm">
      <p className="rounded border border-status-warning bg-status-warning-bg px-3 py-2 text-status-warning">
        {sinTc} movimientos sin tipo de cambio no suman en dólares
        {data.ultimaFechaCotizacion && ` (la serie de dólar BNA llega hasta el ${formatFecha(data.ultimaFechaCotizacion)})`}. Las
        celdas afectadas están marcadas con ⚠.
      </p>
    </div>
  );
}

function TablaRubros({
  data,
  fmt,
  onCelda,
}: {
  data: FlujoPorRubro;
  fmt: (v: number | null | undefined) => string;
  onCelda: (c: Celda) => void;
}) {
  const per = data.periodos;
  const sinTc = new Set(data.sinTipoCambio.map((s) => `${s.periodo}|${s.seccion}|${s.centroCosto ?? ""}|${s.rubro}`));
  const num = (v: number | null | undefined) => (
    <span className={v != null && v < 0 ? "text-status-danger" : undefined}>{fmt(v)}</span>
  );
  const primera = "sticky left-0 z-10 bg-surface px-3 py-1.5 text-left";
  const td = "px-3 py-1.5 text-right whitespace-nowrap";

  const filaTotal = (etiqueta: string, valores: Record<string, number | null>, total?: number | null, clase = "font-semibold") => (
    <tr className={`border-t border-border ${clase}`}>
      <td className={primera}>{etiqueta}</td>
      {per.map((p) => (
        <td key={p} className={td}>
          {num(valores[p])}
        </td>
      ))}
      <td className={td}>{total === undefined ? "" : num(total)}</td>
    </tr>
  );

  const filaRubro = (f: FilaRubro, seccion: SeccionRubro, centroCosto?: string, sangria = false) => (
    <tr key={`${seccion}|${centroCosto}|${f.rubro}`} className={`border-t border-border ${SIN_APLICAR.has(f.rubro) ? "bg-status-warning-bg" : ""}`}>
      <td className={`${primera} ${sangria ? "pl-8" : ""} ${SIN_APLICAR.has(f.rubro) ? "bg-status-warning-bg italic" : ""}`}>{f.rubro}</td>
      {per.map((p) => {
        const marcada = sinTc.has(`${p}|${seccion}|${centroCosto ?? ""}|${f.rubro}`);
        return (
          <td key={p} className={td}>
            {f.valores[p] || marcada ? (
              <button type="button" className="hover:underline" onClick={() => onCelda({ periodo: p, seccion, rubro: f.rubro, centroCosto })}>
                {num(f.valores[p])}
                {marcada && <span title="Hay movimientos sin tipo de cambio"> ⚠</span>}
              </button>
            ) : (
              <span className="text-ink-muted">–</span>
            )}
          </td>
        );
      })}
      <td className={`${td} font-medium`}>{num(f.total)}</td>
    </tr>
  );

  const titulo = (t: string) => (
    <tr className="border-t border-border bg-finance-light">
      <td className={`${primera} bg-finance-light font-semibold text-finance`} colSpan={1}>
        {t}
      </td>
      <td colSpan={per.length + 1} />
    </tr>
  );

  return (
    <div className="overflow-x-auto rounded-md border border-border">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="bg-surface-sunken">
            <th className={`${primera} bg-surface-sunken`}>Rubro</th>
            {per.map((p) => (
              <th key={p} className="px-3 py-2 text-right font-medium">
                {p}
              </th>
            ))}
            <th className="px-3 py-2 text-right font-medium">Total</th>
          </tr>
        </thead>
        <tbody>
          {titulo("Saldo inicial")}
          {data.saldoInicial.cuentas.map((c) => (
            <tr key={c.cuenta} className="border-t border-border">
              <td className={primera} title={c.aclaracion ?? undefined}>
                {c.cuenta}
                {c.aclaracion && <span className="ml-1 text-xs text-ink-secondary">ⓘ</span>}
              </td>
              <td className={td}>{num(c.importe)}</td>
              <td colSpan={per.length} />
            </tr>
          ))}
          <tr className="border-t border-border font-semibold">
            <td className={primera}>Total saldo inicial</td>
            <td className={td}>{num(data.saldoInicial.total)}</td>
            <td colSpan={per.length} />
          </tr>

          {titulo("Ingresos")}
          <IngresosConSecciones
            rubros={data.ingresos.rubros}
            periodos={per}
            primera={primera}
            td={td}
            num={num}
            filaRubro={filaRubro}
          />
          {filaTotal("Total ingresos", data.ingresos.totalPorPeriodo, sumar(data.ingresos.totalPorPeriodo))}

          {titulo("Egresos")}
          {data.egresos.centrosCosto.map((g) => (
            <GrupoFilas key={g.centroCosto} nombre={g.centroCosto} primera={primera} colSpan={per.length + 1}>
              {g.rubros.map((f) => filaRubro(f, "egresos", g.centroCosto, true))}
              {filaTotal(`Subtotal ${g.centroCosto}`, g.subtotalPorPeriodo, g.subtotal, "font-medium")}
            </GrupoFilas>
          ))}
          {filaTotal("Total egresos", data.egresos.totalPorPeriodo, sumar(data.egresos.totalPorPeriodo))}

          {filaTotal("Neto operativo", data.netoOperativoPorPeriodo, sumar(data.netoOperativoPorPeriodo), "font-semibold bg-surface-sunken")}

          {titulo("Movimientos entre cuentas propias")}
          {data.internos.rubros.map((f) => filaRubro(f, "internos"))}

          {titulo("Saldo final")}
          {Object.entries(data.saldoFinalPorCuenta).map(([cuenta, valores]) => filaTotal(cuenta, valores, undefined, ""))}
          {filaTotal("Total saldo final", data.saldoFinalPorPeriodo)}
        </tbody>
      </table>
    </div>
  );
}

function GrupoFilas({
  nombre,
  primera,
  colSpan,
  children,
}: {
  nombre: string;
  primera: string;
  colSpan: number;
  children: React.ReactNode;
}) {
  return (
    <>
      <tr className="border-t border-border">
        <td className={`${primera} font-medium`}>{nombre}</td>
        <td colSpan={colSpan} />
      </tr>
      {children}
    </>
  );
}

function sumar(valores: Record<string, number>): number {
  return Math.round(Object.values(valores).reduce((a, v) => a + v, 0) * 100) / 100;
}


function IngresosConSecciones({
  rubros,
  periodos,
  primera,
  td,
  num,
  filaRubro,
}: {
  rubros: FilaRubro[];
  periodos: string[];
  primera: string;
  td: string;
  num: (v: number | null | undefined) => React.ReactNode;
  filaRubro: (f: FilaRubro, seccion: SeccionRubro, centroCosto?: string, sangria?: boolean) => React.ReactNode;
}) {
  const [expandGranos, setExpandGranos] = useState(true);
  const [expandHacienda, setExpandHacienda] = useState(true);

  const esGrano = (r: string) =>
    r === "Venta Granos" ||
    r === "Venta Soja" ||
    r === "Venta Maiz" ||
    r === "Venta Maíz" ||
    r === "Venta Girasol" ||
    r === "Venta Trigo" ||
    r === "Venta Cebada" ||
    r === "Venta Avena" ||
    r === "Venta Sorgo";

  const esHacienda = (r: string) =>
    r.startsWith("Venta ") && !esGrano(r);

  const rubrosGranos = rubros.filter((f) => esGrano(f.rubro));
  const rubrosHacienda = rubros.filter((f) => esHacienda(f.rubro));
  const otrosRubros = rubros.filter((f) => !esGrano(f.rubro) && !esHacienda(f.rubro));

  const subtotalGrupo = (filas: FilaRubro[]) => {
    const vals: Record<string, number> = {};
    for (const p of periodos) {
      vals[p] = Math.round(filas.reduce((acc, f) => acc + (f.valores[p] || 0), 0) * 100) / 100;
    }
    const tot = Math.round(filas.reduce((acc, f) => acc + (f.total || 0), 0) * 100) / 100;
    return { valores: vals, total: tot };
  };

  const filaCabeceraGrupo = (
    titulo: string,
    expandido: boolean,
    onToggle: () => void,
    filas: FilaRubro[]
  ) => {
    if (filas.length === 0) return null;
    const sub = subtotalGrupo(filas);
    return (
      <tr className="border-t border-border bg-surface-sunken/40 font-medium">
        <td className={primera}>
          <button
            type="button"
            onClick={onToggle}
            className="flex items-center gap-1.5 font-semibold text-ink hover:text-agro"
          >
            <span>{expandido ? "▾" : "▸"}</span>
            <span>{titulo}</span>
            <span className="text-xs text-ink-muted">({filas.length})</span>
          </button>
        </td>
        {periodos.map((p) => (
          <td key={p} className={`${td} font-semibold`}>
            {num(sub.valores[p] || 0)}
          </td>
        ))}
        <td className={`${td} font-semibold`}>{num(sub.total)}</td>
      </tr>
    );
  };

  return (
    <>
      {rubrosGranos.length > 0 && (
        <>
          {filaCabeceraGrupo("Venta Granos", expandGranos, () => setExpandGranos(!expandGranos), rubrosGranos)}
          {expandGranos && rubrosGranos.map((f) => filaRubro(f, "ingresos", undefined, true))}
        </>
      )}

      {rubrosHacienda.length > 0 && (
        <>
          {filaCabeceraGrupo("Venta Hacienda", expandHacienda, () => setExpandHacienda(!expandHacienda), rubrosHacienda)}
          {expandHacienda && rubrosHacienda.map((f) => filaRubro(f, "ingresos", undefined, true))}
        </>
      )}

      {otrosRubros.map((f) => filaRubro(f, "ingresos"))}
    </>
  );
}
