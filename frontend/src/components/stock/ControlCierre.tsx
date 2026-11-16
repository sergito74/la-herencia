"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatCantidad, formatFecha } from "@/lib/format";
import { apiGet } from "@/services/apiClient";

interface RemitoSinFactura {
  idRemito: number;
  fecha: string;
  remito: string;
  proveedor: string | null;
  productos: string[];
}
interface UsadoSinRemito {
  idProducto: number;
  producto: string;
  unidad: string | null;
  ordenes: { idOrdenTrabajo: number; fecha: string; cantidad: number }[];
}

const fetchPendientes = () =>
  apiGet<{ remitosSinFactura: RemitoSinFactura[]; usadosSinRemito: UsadoSinRemito[] }>("/api/stock/pendientes-carga");

/** 050: lo que falta cargar para que el costo de los insumos cierre. Solo acciones concretas, por documento. */
export function ControlCierre() {
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["pendientes-carga"], queryFn: fetchPendientes, staleTime: 0 });
  if (isLoading) return <LoadingState />;
  if (isError) return <ErrorState message="No se pudieron consultar los pendientes." onRetry={() => refetch()} />;
  const remitos = data?.remitosSinFactura ?? [];
  const usados = data?.usadosSinRemito ?? [];

  if (!remitos.length && !usados.length) {
    return <p className="rounded border bg-white p-4 text-sm">No hay nada pendiente de carga.</p>;
  }
  return (
    <div className="space-y-6">
      {remitos.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-base font-semibold">Facturas que faltan cargar</h2>
          <p className="text-sm text-ink-secondary">Llegó la mercadería y no hay factura. Cargala y vinculala al remito.</p>
          <ul className="divide-y rounded border bg-white text-sm">
            {remitos.map((r) => (
              <li key={r.idRemito} className="flex flex-wrap items-center justify-between gap-2 p-3">
                <span>
                  <strong>{r.proveedor}</strong> · remito {r.remito} del {formatFecha(r.fecha)} · {r.productos.join(", ")}
                </span>
                <Link className="text-finance underline" href={`/produccion/remitos/${r.idRemito}`}>
                  Abrir el remito
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
      {usados.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-base font-semibold">Insumos usados sin remito de entrada</h2>
          <p className="text-sm text-ink-secondary">Una orden usó un producto que nunca entró al galpón: falta el remito o la orden tiene otro producto.</p>
          <ul className="divide-y rounded border bg-white text-sm">
            {usados.flatMap((u) =>
              u.ordenes.map((o) => (
                <li key={`${u.idProducto}-${o.idOrdenTrabajo}`} className="flex flex-wrap items-center justify-between gap-2 p-3">
                  <span>
                    <strong>{u.producto}</strong>: {formatCantidad(o.cantidad)} {u.unidad ?? ""} en la orden N° {o.idOrdenTrabajo} del {formatFecha(o.fecha)}
                  </span>
                  <Link className="text-finance underline" href={`/produccion/ordenes/${o.idOrdenTrabajo}`}>
                    Abrir la orden
                  </Link>
                </li>
              )),
            )}
          </ul>
        </section>
      )}
    </div>
  );
}
