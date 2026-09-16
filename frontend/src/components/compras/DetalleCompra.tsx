"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchCompraDetalle, type LineaCompra } from "@/services/comprasApi";
import { TrazabilidadCompra } from "@/components/compras/TrazabilidadCompra";

/**
 * Compra detail: header + lines with explicit imputacion (US2: FR-003,
 * FR-004, FR-006, FR-007). A null imputacion is always rendered as
 * "Sin imputar", never hidden.
 */
export function DetalleCompra({ idCompra }: { idCompra: number }) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["compra", idCompra],
    queryFn: () => fetchCompraDetalle(idCompra),
  });

  if (isLoading) return <p className="text-slate-600">Cargando…</p>;

  if (isError) {
    const message = (error as Error)?.message ?? "";
    if (message.includes("404")) {
      return (
        <p className="rounded border border-slate-200 bg-white p-6 text-center text-slate-600">
          Compra no encontrada.
        </p>
      );
    }
    return <p className="text-red-700">Ocurrió un error al cargar la compra: {message}</p>;
  }

  if (!data) return null;

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="text-lg font-semibold">Compra #{data.idCompra}</h2>
        <dl className="mt-2 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
          <div>
            <dt className="text-slate-500">Fecha</dt>
            <dd>{data.fecha ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Proveedor</dt>
            <dd>{data.proveedor?.razonSocial ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Tipo documento</dt>
            <dd>{data.tipoDocumento ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Nro. documento</dt>
            <dd>{data.numeroDocumento ?? "—"}</dd>
          </div>
        </dl>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="text-sm font-semibold text-slate-700">
          Conceptos diferenciados (FR-007)
        </h3>
        <dl className="mt-2 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
          <div>
            <dt className="text-slate-500">Conceptos no gravados</dt>
            <dd>{data.conceptosNoGravados ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Ingresos brutos</dt>
            <dd>{data.ingresosBrutos ?? "—"}</dd>
          </div>
        </dl>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="text-sm font-semibold text-slate-700">
          Líneas de detalle
        </h3>
        <div className="mt-2 overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-100 text-left">
              <tr>
                <th className="px-3 py-2">Producto/Servicio</th>
                <th className="px-3 py-2">Cantidad</th>
                <th className="px-3 py-2">Precio unitario</th>
                <th className="px-3 py-2">IVA</th>
                <th className="px-3 py-2">Imputación</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.lineas.map((linea) => (
                <LineaRow key={linea.idDetalleCompra} linea={linea} />
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <TrazabilidadCompra idCompra={data.idCompra} />
    </div>
  );
}

function LineaRow({ linea }: { linea: LineaCompra }) {
  return (
    <tr className="align-top hover:bg-slate-50">
      <td className="px-3 py-2">{linea.productoServicio ?? "—"}</td>
      <td className="px-3 py-2">{linea.cantidad ?? "—"}</td>
      <td className="px-3 py-2">{linea.precioUnitario ?? "—"}</td>
      <td className="px-3 py-2">{linea.iva ?? "—"}</td>
      <td className="px-3 py-2">
        {linea.imputacion ? (
          <ul className="space-y-0.5">
            <li>Rubro: {linea.imputacion.rubro ?? "—"}</li>
            <li>
              Centro de costo:{" "}
              {linea.imputacion.centroCosto ?? (
                <span className="italic text-slate-500">Sin asignar</span>
              )}
            </li>
            <li>
              Destino:{" "}
              {linea.imputacion.destino ?? (
                <span className="italic text-slate-500">Sin asignar</span>
              )}
            </li>
            <li>
              Campaña:{" "}
              {linea.imputacion.campania ?? (
                <span className="italic text-slate-500">Sin asignar</span>
              )}
            </li>
          </ul>
        ) : (
          <span className="italic text-slate-500">Sin imputar</span>
        )}
      </td>
    </tr>
  );
}
