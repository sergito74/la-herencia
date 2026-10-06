"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import {
  fetchMovimientos,
  urlExportarValoresPropios,
  type Medio,
  type MovimientoPorMedio,
} from "@/services/tesoreriaApi";
import { ConciliarMovimiento } from "@/components/tesoreria/ConciliarMovimiento";
import { ReferenciaOrigen } from "@/components/tesoreria/ReferenciaOrigen";
import { VincularTraspasoInterno } from "@/components/tesoreria/VincularTraspasoInterno";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { FilterBar, FilterField, filterInputClass } from "@/components/ui/FilterBar";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatFecha, formatMoneda } from "@/lib/format";
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

// Debe (rojo) para negativos, Haber (verde) para positivos — mismo
// criterio que Cuentas Corrientes (débito/crédito).
function celdaDebe(importe: number | null | undefined) {
  return importe != null && importe < 0 ? (
    <span className="text-status-danger">{formatMoneda(Math.abs(importe))}</span>
  ) : (
    "—"
  );
}
function celdaHaber(importe: number | null | undefined) {
  return importe != null && importe > 0 ? (
    <span className="text-status-success">{formatMoneda(importe)}</span>
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
        {
          key: "extracto",
          header: "Extracto",
          render: (m: any) => {
            const url = urlExtractoBna(m.fechaHora);
            return url ? (
              <a href={url} target="_blank" rel="noopener noreferrer" className="text-finance underline">
                Ver PDF
              </a>
            ) : (
              "—"
            );
          },
        },
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
        {
          key: "extracto",
          header: "Resumen",
          render: (m: any) => {
            const url = urlResumenMercadoLibre(m.fecha);
            return url ? (
              <a href={url} target="_blank" rel="noopener noreferrer" className="text-finance underline">
                Ver PDF
              </a>
            ) : (
              "—"
            );
          },
        },
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
  const [expandedId, setExpandedId] = useState<number | null>(highlightKey ?? null);
  const pageSize = 50;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["tesoreria-movimientos", medio, fechaDesde, fechaHasta, page, pageSize],
    queryFn: () =>
      fetchMovimientos(medio, {
        fechaDesde: fechaDesde || undefined,
        fechaHasta: fechaHasta || undefined,
        page,
        pageSize,
      }),
  });

  const idField = idFieldFor(medio);

  const columns: DataTableColumn<MovimientoPorMedio[typeof medio]>[] = [
    ...columnsFor(medio).map((col) => ({
      key: col.key,
      header: col.header,
      numeric: col.numeric,
      wrap: col.wrap,
      render: col.render,
    })),
    {
      key: "referencia",
      header: "Referencia de origen",
      wrap: true,
      render: (item: any) => {
        const id = item[idField] as number;
        return expandedId === id ? (
          <ReferenciaOrigen medio={medio} idMovimiento={id} />
        ) : (
          <button className="text-finance underline" onClick={() => setExpandedId(id)}>
            Ver referencia
          </button>
        );
      },
    },
    // Tarjetas se concilia exclusivamente desde su propio flujo (008/009,
    // FR-002) — no se ofrecen estas dos columnas para ese medio (024
    // tampoco soporta Tarjetas, mismo criterio).
    ...(medio !== "tarjetas"
      ? [
          {
            key: "conciliacion",
            header: "Conciliación",
            wrap: true,
            render: (item: any) => (
              <ConciliarMovimiento medio={medio} idMovimiento={item[idField] as number} estadoExterno={item.estadoConciliacion} />
            ),
          },
          {
            key: "traspasoInterno",
            header: "Traspaso interno",
            wrap: true,
            render: (item: any) => (
              <VincularTraspasoInterno medio={medio} idMovimiento={item[idField] as number} estadoExterno={item.estadoConciliacion} />
            ),
          },
        ]
      : []),
  ];

  return (
    <div className="space-y-4">
      <FilterBar onSubmit={(e) => e.preventDefault()}>
        <FilterField label="Fecha desde">
          <input
            type="date"
            className={filterInputClass}
            value={fechaDesde}
            onChange={(e) => {
              setPage(1);
              setFechaDesde(e.target.value);
            }}
          />
        </FilterField>
        <FilterField label="Fecha hasta">
          <input
            type="date"
            className={filterInputClass}
            value={fechaHasta}
            onChange={(e) => {
              setPage(1);
              setFechaHasta(e.target.value);
            }}
          />
        </FilterField>
        {medio === "valores-propios" && (
          <a
            href={urlExportarValoresPropios({
              fechaDesde: fechaDesde || undefined,
              fechaHasta: fechaHasta || undefined,
            })}
            className="self-end rounded border border-border px-3 py-1.5 text-sm hover:bg-surface-sunken"
          >
            Exportar a Excel
          </a>
        )}
      </FilterBar>

      {isLoading && <LoadingState />}
      {isError && (
        <ErrorState message="Ocurrió un error al buscar movimientos." onRetry={() => refetch()} />
      )}

      {data && (
        <DataTable
          columns={columns}
          rows={data.items}
          keyField={(item: any) => item[idField]}
          emptyMessage={`Sin movimientos para ${MEDIO_LABELS[medio]} en este rango.`}
          page={data.page}
          pageSize={data.pageSize}
          total={data.total}
          onPageChange={setPage}
          highlightKey={highlightKey}
        />
      )}
    </div>
  );
}

export { MEDIO_LABELS };
