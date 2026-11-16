"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatCantidad, formatFecha } from "@/lib/format";
import { apiGet } from "@/services/apiClient";

interface FilaControl {
  idProducto: number;
  producto: string;
  tipo: string | null;
  unidad: string | null;
  facturado: number;
  facturadoSinRemito: number;
  remitido: number;
  remitidoSinFactura: number;
  usado: number;
  faltante: number;
  sobrante: number;
  existencia: number;
  ultimoRecuento: { fecha: string; contado: number; sistema: number } | null;
  alertas: string[];
}

const fetchControl = () => apiGet<{ desde: string; items: FilaControl[]; conAlertas: number }>("/api/stock/control-cierre");

const n = (v: number) => (Math.abs(v) > 0.0005 ? formatCantidad(v) : "—");

/** 050: control de cierre por producto desde la activación de la imputación automática. */
export function ControlCierre() {
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["control-cierre"], queryFn: fetchControl, staleTime: 0 });
  const [soloAlertas, setSoloAlertas] = useState(true);

  const columnas: DataTableColumn<FilaControl>[] = [
    {
      key: "producto",
      header: "Producto",
      sortValue: (f) => f.producto,
      render: (f) => f.producto,
    },
    { key: "unidad", header: "Unidad", render: (f) => f.unidad ?? "—" },
    { key: "facturado", header: "Facturado", numeric: true, align: "right", render: (f) => n(f.facturado) },
    { key: "remitido", header: "Remitido", numeric: true, align: "right", render: (f) => n(f.remitido) },
    { key: "usado", header: "Usado por órdenes", numeric: true, align: "right", render: (f) => n(f.usado) },
    {
      key: "recuento",
      header: "Faltante / sobrante sin órdenes",
      numeric: true,
      align: "right",
      render: (f) => (f.faltante || f.sobrante ? `−${n(f.faltante)} / +${n(f.sobrante)}` : "—"),
    },
    {
      key: "existencia",
      header: "Stock del sistema",
      numeric: true,
      align: "right",
      render: (f) => <span className={f.existencia < -0.0005 ? "text-status-danger" : ""}>{n(f.existencia)}</span>,
    },
    {
      key: "ultimo",
      header: "Último recuento",
      numeric: true,
      render: (f) => (f.ultimoRecuento ? `${formatFecha(f.ultimoRecuento.fecha)}: ${formatCantidad(f.ultimoRecuento.contado)}` : "—"),
    },
    {
      key: "alertas",
      header: "Qué revisar",
      wrap: true,
      render: (f) => (
        <div className="space-y-0.5 text-xs">
          {f.facturadoSinRemito > 0.0005 && <div className="text-amber-800">Facturado sin remito: {formatCantidad(f.facturadoSinRemito)}</div>}
          {f.remitidoSinFactura > 0.0005 && <div className="text-amber-800">Remitido sin factura: {formatCantidad(f.remitidoSinFactura)}</div>}
          {(f.faltante > 0.0005 || f.sobrante > 0.0005) && <div className="text-amber-800">Recuento sin órdenes para repartir</div>}
          {f.existencia < -0.0005 && <div className="text-status-danger">Stock negativo: se usó sin remito de entrada</div>}
        </div>
      ),
    },
  ];

  if (isLoading) return <LoadingState />;
  if (isError) return <ErrorState message="No se pudo calcular el control de cierre." onRetry={() => refetch()} />;
  const filas = (data?.items ?? []).filter((f) => !soloAlertas || f.alertas.length > 0);

  return (
    <div className="space-y-4">
      <p className="text-sm text-ink-secondary">
        Por producto, desde el {formatFecha(data?.desde)} (recuento de apertura): lo facturado, lo remitido, lo que usaron
        las órdenes (con los ajustes de recuento) y el stock. Marca lo que no cierra: facturas sin remito (no llegó o quedó
        en el proveedor), remitos sin factura (falta cargarla), recuentos sin órdenes para repartir y stock negativo.
      </p>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={soloAlertas} onChange={(e) => setSoloAlertas(e.target.checked)} />
        Solo productos con algo para revisar ({data?.conAlertas ?? 0} de {data?.items.length ?? 0})
      </label>
      <DataTable
        columns={columnas}
        rows={filas}
        keyField={(f) => f.idProducto}
        emptyMessage="Todo cierra."
        page={1}
        pageSize={Math.max(filas.length, 1)}
        total={filas.length}
        onPageChange={() => undefined}
      />
    </div>
  );
}
