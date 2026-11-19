"use client";

import { useQuery } from "@tanstack/react-query";
import { RangoFechas } from "@/components/ui/RangoFechas";
import { TiraIndicadores } from "@/components/ui/TiraIndicadores";
import { SideDrawer } from "@/components/ui/SideDrawer";
import { useEffect, useState } from "react";

import {
  fetchMovimientos,
  fetchResumenMedio,
  urlExportarValoresPropios,
  type Medio,
  type MovimientoPorMedio,
} from "@/services/tesoreriaApi";
import { ConciliarMovimiento } from "@/components/tesoreria/ConciliarMovimiento";
import { ReferenciaOrigen } from "@/components/tesoreria/ReferenciaOrigen";
import { VincularTraspasoInterno } from "@/components/tesoreria/VincularTraspasoInterno";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatCantidad, formatFecha, formatMoneda } from "@/lib/format";
import { urlDocumentoLocal } from "@/services/comprasApi";

// Carpetas reales donde viven los resúmenes/extractos originales en esta
// PC (pedido explícito del usuario: poder controlar lo cargado contra la
// fuente de verdad) — un PDF por mes en cada una, confirmado contra el
// disco real. El nombre de archivo varía por banco/medio, de ahí el
// parámetro `nombreArchivo`.
const BASE_EXTRACTOS_BNA = "C:\\Users\\Sergio\\Dropbox\\Giamigli de Bolivar SA\\Bancos\\BNA\\Extractos\\";
const BASE_RESUMENES_MERCADO_LIBRE = "C:\\Users\\Sergio\\Dropbox\\Giamigli de Bolivar SA\\Bancos\\Mercado Libre\\Resumenes\\";

function urlExtractoMensual(
  fecha: string | null | undefined,
  base: string,
  nombreArchivo: (anio: string, mes: string) => string
): string | null {
  if (!fecha) return null;
  const match = fecha.match(/^(\d{4})-(\d{2})/);
  if (!match) return null;
  const [, anio, mes] = match;
  return urlDocumentoLocal(`${base}${anio}\\${nombreArchivo(anio, mes)}`);
}

function urlExtractoBna(fechaHora: string | null | undefined): string | null {
  return urlExtractoMensual(fechaHora, BASE_EXTRACTOS_BNA, (anio, mes) => `Extracto ${anio} ${mes}.pdf`);
}

function urlResumenMercadoLibre(fecha: string | null | undefined): string | null {
  return urlExtractoMensual(fecha, BASE_RESUMENES_MERCADO_LIBRE, (anio, mes) => `${anio} ${mes}.pdf`);
}

// Debe y Haber en el color de texto normal (18/11/2026: el rojo queda solo para alertas).
function celdaDebe(importe: number | null | undefined) {
  return importe != null && importe < 0 ? (
    <span>{formatMoneda(Math.abs(importe))}</span>
  ) : (
    "—"
  );
}
function celdaHaber(importe: number | null | undefined) {
  return importe != null && importe > 0 ? (
    <span>{formatMoneda(importe)}</span>
  ) : (
    "—"
  );
}
function celdaMoneda(importe: number | null | undefined) {
  return importe != null ? formatMoneda(importe) : "—";
}

const MEDIO_LABELS: Record<Medio, string> = {
  bna: "Banco Nación",
  galicia: "Galicia",
  "mercado-libre": "Mercado Libre",
  efectivo: "Pagos en efectivo",
  "valores-propios": "Valores propios",
  "valores-recibidos": "Valores recibidos",
  tarjetas: "Tarjetas",
};

interface ColumnDef {
  key: string;
  header: string;
  numeric?: boolean;
  wrap?: boolean;
  render: (item: any) => React.ReactNode;
}

function columnsFor(medio: Medio): ColumnDef[] {
  switch (medio) {
    case "bna":
      return [
        { key: "fechaHora", header: "Fecha", numeric: true, render: (m: any) => formatFecha(m.fechaHora) },
        { key: "concepto", header: "Concepto", render: (m: any) => m.concepto ?? "—" },
        { key: "debe", header: "Debe", numeric: true, render: (m: any) => celdaDebe(m.importe) },
        { key: "haber", header: "Haber", numeric: true, render: (m: any) => celdaHaber(m.importe) },
        { key: "saldo", header: "Saldo", numeric: true, render: (m: any) => celdaMoneda(m.saldo) },
        { key: "contacto", header: "Contacto", render: (m: any) => m.contacto ?? "—" },
      ];
    case "galicia":
      return [
        { key: "fecha", header: "Fecha", numeric: true, render: (m: any) => formatFecha(m.fecha) },
        { key: "descripcion", header: "Descripción", render: (m: any) => m.descripcion ?? "—" },
        { key: "debitos", header: "Débitos", numeric: true, render: (m: any) => celdaMoneda(m.debitos) },
        { key: "creditos", header: "Créditos", numeric: true, render: (m: any) => celdaMoneda(m.creditos) },
        { key: "saldo", header: "Saldo", numeric: true, render: (m: any) => celdaMoneda(m.saldo) },
        { key: "contacto", header: "Contacto", render: (m: any) => m.contacto ?? "—" },
      ];
    case "mercado-libre":
      return [
        { key: "fecha", header: "Fecha", numeric: true, render: (m: any) => formatFecha(m.fecha) },
        {
          key: "descripcion", header: "Descripción",
          render: (m: any) => (
            <span>
              {m.descripcion ?? "—"}
              {m.esConducto && (
                <span title="La billetera solo hizo de puente entre un banco propio y el pago: no es un pago propio de Mercado Pago"
                  className="ml-2 rounded border border-line px-1 text-xs text-ink-secondary">Conducto</span>
              )}
            </span>
          ),
        },
        { key: "debe", header: "Debe", numeric: true, render: (m: any) => celdaDebe(m.importe) },
        { key: "haber", header: "Haber", numeric: true, render: (m: any) => celdaHaber(m.importe) },
        { key: "saldo", header: "Saldo", numeric: true, render: (m: any) => celdaMoneda(m.saldo) },
        { key: "contacto", header: "Contacto", render: (m: any) => m.contacto ?? "—" },
      ];
    case "efectivo":
      return [
        { key: "fecha", header: "Fecha", numeric: true, render: (m: any) => formatFecha(m.fecha) },
        { key: "cuenta", header: "Cuenta", render: (m: any) => m.cuenta ?? "—" },
        { key: "caja", header: "Caja", render: (m: any) => m.caja ?? "—" },
        { key: "numeroDocumento", header: "Nro. documento", numeric: true, render: (m: any) => m.numeroDocumento ?? "—" },
        { key: "debe", header: "Debe", numeric: true, render: (m: any) => celdaDebe(m.importeImputado) },
        { key: "haber", header: "Haber", numeric: true, render: (m: any) => celdaHaber(m.importeImputado) },
      ];
    case "valores-propios":
      return [
        { key: "numeroCheque", header: "Nro. cheque", numeric: true, render: (m: any) => m.numeroCheque ?? "—" },
        { key: "fechaEmision", header: "Emisión", numeric: true, render: (m: any) => formatFecha(m.fechaEmision) },
        { key: "fechaVencimiento", header: "Vencimiento", numeric: true, render: (m: any) => formatFecha(m.fechaVencimiento) },
        { key: "importe", header: "Importe", numeric: true, render: (m: any) => celdaMoneda(m.importe) },
        { key: "cobrado", header: "Cobrado", render: (m: any) => m.cobrado ?? "—" },
        { key: "fechaCobro", header: "Fecha cobro", numeric: true, render: (m: any) => formatFecha(m.fechaCobro) },
        { key: "numeroCuenta", header: "Nro. cuenta", render: (m: any) => m.numeroCuenta ?? "—" },
        { key: "comentarios", header: "Comentarios", wrap: true, render: (m: any) => m.comentarios ?? "—" },
      ];
    case "valores-recibidos":
      return [
        { key: "numeroValor", header: "Nro. valor", numeric: true, render: (m: any) => m.numeroValor ?? "—" },
        { key: "banco", header: "Banco", render: (m: any) => m.banco ?? "—" },
        { key: "fechaEmision", header: "Emisión", numeric: true, render: (m: any) => formatFecha(m.fechaEmision) },
        { key: "fechaVencimiento", header: "Vencimiento", numeric: true, render: (m: any) => formatFecha(m.fechaVencimiento) },
        { key: "fechaCobro", header: "Cobro", numeric: true, render: (m: any) => formatFecha(m.fechaCobro) },
        { key: "importe", header: "Importe", numeric: true, render: (m: any) => celdaMoneda(m.importe) },
        { key: "destino", header: "Destino", render: (m: any) => m.destino ?? "—" },
      ];
    case "tarjetas":
      return [
        { key: "fechaCompra", header: "Fecha compra", numeric: true, render: (m: any) => formatFecha(m.fechaCompra) },
        { key: "detalle", header: "Detalle", render: (m: any) => m.detalle ?? "—" },
        { key: "importe", header: "Importe", numeric: true, render: (m: any) => celdaMoneda(m.importe) },
        { key: "numeroDocumento", header: "Nro. documento", numeric: true, render: (m: any) => m.numeroDocumento ?? "—" },
      ];
  }
}

function idFieldFor(medio: Medio): string {
  switch (medio) {
    case "bna":
      return "idMovimientoBNA";
    case "galicia":
    case "mercado-libre":
      return "idMovimiento";
    case "efectivo":
      return "idPagoEfectivo";
    case "valores-propios":
    case "valores-recibidos":
      return "idValor";
    case "tarjetas":
      return "idLineaConsumo";
  }
}

export function MovimientosPorMedio({
  medio,
  highlightKey,
}: {
  medio: Medio;
  highlightKey?: number;
}) {
  const [fechaDesde, setFechaDesde] = useState("");
  const [fechaHasta, setFechaHasta] = useState("");
  const [page, setPage] = useState(1);
  // 19/11/2026: ver solo lo que falta conciliar (Tarjetas se concilia en su propia pantalla).
  const conciliable = medio !== "tarjetas";
  const [soloPendientes, setSoloPendientes] = useState(false);
  const [buscar, setBuscar] = useState("");
  const [q, setQ] = useState("");
  useEffect(() => { const t = setTimeout(() => { setPage(1); setQ(buscar.trim()); }, 350); return () => clearTimeout(t); }, [buscar]);
  const resumen = useQuery({ queryKey: ["tesoreria-resumen", medio], queryFn: () => fetchResumenMedio(medio) });
  // 19/11/2026 (auditoría de Tesorería, mejora 3): el detalle del movimiento se abre en un panel lateral.
  const [abierto, setAbierto] = useState<any | null>(null);
  const pageSize = 50;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["tesoreria-movimientos", medio, fechaDesde, fechaHasta, page, pageSize, soloPendientes, q],
    queryFn: () =>
      fetchMovimientos(medio, {
        fechaDesde: fechaDesde || undefined,
        fechaHasta: fechaHasta || undefined,
        page,
        pageSize,
        estado: soloPendientes ? "pendientes" : undefined,
        q: q || undefined,
      }),
  });

  const idField = idFieldFor(medio);

  const columns: DataTableColumn<MovimientoPorMedio[typeof medio]>[] = [
    ...columnsFor(medio).map((col) => ({
      key: col.key,
      header: col.header,
      numeric: col.numeric,
      align: (col.numeric && !/fecha/i.test(col.key) ? "right" : undefined) as "right" | undefined,
      wrap: col.wrap,
      render: col.render,
    })),
    // Tarjetas se concilia exclusivamente desde su propio flujo (008/009,
    // FR-002) — no se ofrecen estas dos columnas para ese medio (024
    // tampoco soporta Tarjetas, mismo criterio).
    ...(medio !== "tarjetas"
      ? [
          {
            key: "conciliacion",
            header: "Conciliación",
            render: (item: any) => (
              <ConciliarMovimiento medio={medio} idMovimiento={item[idField] as number} estadoExterno={item.estadoConciliacion}
                idContacto={item.idContacto ?? null} contacto={item.contacto ?? null} />
            ),
          },
        ]
      : []),
  ];

  const r = resumen.data;
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        {r && (
          <TiraIndicadores compacta items={[
            { titulo: "Saldo", valor: r.saldo != null ? formatMoneda(r.saldo) : "—", pie: r.ultimoMovimiento ? `al ${formatFecha(String(r.ultimoMovimiento))}` : undefined },
            ...(conciliable && r.pendientes != null ? [{
              titulo: "Sin conciliar", valor: formatCantidad(r.pendientes), aviso: !!r.pendientes, activo: soloPendientes,
              pie: `${r.pendientes ? `${formatMoneda(r.importePendiente ?? 0)}${r.pendienteMasViejo ? ` · desde ${formatFecha(String(r.pendienteMasViejo))}` : ""} · ` : ""}clic para ${soloPendientes ? "ver todos" : "ver solo los pendientes"}`,
              onClick: () => { setPage(1); setSoloPendientes(!soloPendientes); },
            }] : []),
            ...(r.ultimaCarga !== undefined ? [{ titulo: "Último extracto", valor: r.ultimaCarga ? formatFecha(String(r.ultimaCarga)) : "—" }] : []),
          ]} />
        )}
        <RangoFechas etiqueta="" valor={{ desde: fechaDesde, hasta: fechaHasta }} onChange={(x) => { setPage(1); setFechaDesde(x.desde); setFechaHasta(x.hasta); }} />
        <input value={buscar} onChange={(e) => setBuscar(e.target.value)} placeholder="Buscar concepto, contacto o importe"
          className="h-8 w-72 rounded-md border border-border bg-surface px-3 text-sm" aria-label="Buscar movimientos" />
        {soloPendientes && <button type="button" onClick={() => { setPage(1); setSoloPendientes(false); }}
          className="h-7 rounded-full bg-finance-light px-2.5 text-xs font-medium text-finance">Solo pendientes ✕</button>}
        {medio === "valores-propios" && (
          <a href={urlExportarValoresPropios({ fechaDesde: fechaDesde || undefined, fechaHasta: fechaHasta || undefined })}
            className="ml-auto h-8 rounded-md border border-border px-3 py-1.5 text-sm hover:bg-surface-sunken">Exportar a Excel</a>
        )}
      </div>

      {isLoading && <LoadingState />}
      {isError && (
        <ErrorState message="Ocurrió un error al buscar movimientos." onRetry={() => refetch()} />
      )}

      {abierto && (
        <SideDrawer open onClose={() => setAbierto(null)} maxWidthClass="max-w-2xl"
          title={String(abierto.concepto ?? abierto.descripcion ?? abierto.detalle ?? "Movimiento")}
          subtitulo={`${formatFecha(abierto.fechaHora ?? abierto.fecha)}${abierto.contacto ? ` · ${abierto.contacto}` : ""}`}>
          <div className="space-y-5 text-sm">
            <p className="font-data text-2xl font-semibold">{formatMoneda(Number(abierto.importe ?? (abierto.creditos || -(abierto.debitos ?? 0)) ?? 0))}</p>
            {medio !== "tarjetas" && (
              <section className="space-y-2">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-muted">Conciliación</h3>
                <ConciliarMovimiento medio={medio} idMovimiento={abierto[idField] as number} />
              </section>
            )}
            <section className="space-y-2">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-muted">De dónde viene</h3>
              <ReferenciaOrigen medio={medio} idMovimiento={abierto[idField] as number} />
            </section>
            {medio !== "tarjetas" && (
              <section className="space-y-2">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-muted">Pase entre cuentas propias</h3>
                <VincularTraspasoInterno medio={medio} idMovimiento={abierto[idField] as number} estadoExterno={abierto.estadoConciliacion} />
              </section>
            )}
          </div>
        </SideDrawer>
      )}

      {data && (
        <DataTable
          columns={columns}
          rows={data.items}
          keyField={(item: any) => item[idField]}
          emptyMessage={soloPendientes ? `No queda nada por conciliar en ${MEDIO_LABELS[medio]} en este rango.` : `Sin movimientos para ${MEDIO_LABELS[medio]} en este rango.`}
          page={data.page}
          pageSize={data.pageSize}
          total={data.total}
          onPageChange={setPage}
          highlightKey={highlightKey}
          onRowClick={(item: any) => setAbierto(item)}
          selectedKey={abierto ? abierto[idField] : null}
          rowActions={(item: any) => {
            const pdf = medio === "bna" ? urlExtractoBna(item.fechaHora) : medio === "mercado-libre" ? urlResumenMercadoLibre(item.fecha) : null;
            return [
              { label: "Ver detalle", onClick: () => setAbierto(item) },
              ...(pdf ? [{ label: "Abrir el extracto del mes", href: pdf }] : []),
            ];
          }}
        />
      )}
    </div>
  );
}

export { MEDIO_LABELS };

