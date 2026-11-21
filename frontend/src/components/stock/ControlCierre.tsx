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

interface ConsumoSinCosto {
  idProducto: number;
  producto: string;
  unidad: string | null;
  cantidad: number;
}
interface FacturaSobreVinculada {
  idCompra: number;
  documento: string;
  fecha: string;
  proveedor: string | null;
  renglon: string;
  cantidad: number;
  vinculada: number;
}
interface VinculoQueNoCorresponde {
  idRemito: number;
  remito: string;
  fecha: string;
  proveedor: string | null;
  producto: string | null;
  idCompra: number;
  documento: string;
  proveedorDocumento: string | null;
  motivo: string;
}

const fetchPendientes = () =>
  apiGet<{
    remitosSinFactura: RemitoSinFactura[];
    usadosSinRemito: UsadoSinRemito[];
    consumosSinCosto?: ConsumoSinCosto[];
    facturasSobreVinculadas?: FacturaSobreVinculada[];
    vinculosQueNoCorresponden?: VinculoQueNoCorresponde[];
  }>("/api/stock/pendientes-carga");

/** 050: lo que falta cargar para que el costo de los insumos cierre. Solo acciones concretas, por documento. */
export function ControlCierre() {
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["pendientes-carga"], queryFn: fetchPendientes, staleTime: 0 });
  if (isLoading) return <LoadingState />;
  if (isError) return <ErrorState message="No se pudieron consultar los pendientes." onRetry={() => refetch()} />;
  const remitos = data?.remitosSinFactura ?? [];
  const usados = data?.usadosSinRemito ?? [];
  const sinCosto = data?.consumosSinCosto ?? [];
  const sobre = data?.facturasSobreVinculadas ?? [];
  const ajenos = data?.vinculosQueNoCorresponden ?? [];

  if (!remitos.length && !usados.length && !sinCosto.length && !sobre.length && !ajenos.length) {
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
      {ajenos.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-base font-semibold">Remitos vinculados a un documento que no corresponde</h2>
          <p className="text-sm text-ink-secondary">
            El remito está vinculado a una factura de otro proveedor, a una nota de débito o crédito, o a un renglón que no se imputa. Cambiá el vínculo a la
            factura de compra de ese remito.
          </p>
          <ul className="divide-y rounded border bg-white text-sm">
            {ajenos.map((v) => (
              <li key={`${v.idRemito}-${v.idCompra}`} className="flex flex-wrap items-center justify-between gap-2 p-3">
                <span>
                  <strong>{v.proveedor}</strong> · remito {v.remito} del {formatFecha(v.fecha)} · {v.producto} → {v.documento} de {v.proveedorDocumento} ({v.motivo})
                </span>
                <Link className="text-finance underline" href={`/produccion/remitos/${v.idRemito}`}>
                  Abrir el remito
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
      {sobre.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-base font-semibold">Facturas vinculadas por más de lo facturado</h2>
          <p className="text-sm text-ink-secondary">Un renglón de factura está vinculado a remitos por más cantidad de la que tiene: esa mercadería se costearía dos veces.</p>
          <ul className="divide-y rounded border bg-white text-sm">
            {sobre.map((f) => (
              <li key={`${f.idCompra}-${f.renglon}`} className="flex flex-wrap items-center justify-between gap-2 p-3">
                <span>
                  <strong>{f.proveedor}</strong> · {f.documento} del {formatFecha(f.fecha)} · {f.renglon}: facturado {formatCantidad(f.cantidad)}, vinculado{" "}
                  {formatCantidad(f.vinculada)}
                </span>
                <Link className="text-finance underline" href={`/compras/${f.idCompra}/editar`}>
                  Abrir la factura
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
      {sinCosto.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-base font-semibold">Insumos usados sin costo</h2>
          <p className="text-sm text-ink-secondary">
            Las órdenes usaron mercadería de un remito que no tiene factura: ese consumo no llega con costo a los cultivos. Se resuelve cargando y vinculando la
            factura del remito (ver arriba).
          </p>
          <ul className="divide-y rounded border bg-white text-sm">
            {sinCosto.map((c) => (
              <li key={c.idProducto} className="p-3">
                <strong>{c.producto}</strong>: {formatCantidad(c.cantidad)} {c.unidad ?? ""} sin costo
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
