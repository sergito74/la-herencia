"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchCompraDetalle, type LineaCompra } from "@/services/comprasApi";
import { TrazabilidadCompra } from "@/components/compras/TrazabilidadCompra";
import { Breadcrumb } from "@/components/ui/Breadcrumb";
import { ContactoLink } from "@/components/ui/ContactoLink";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";

/**
 * Compra detail: header + lines with explicit imputacion (US2: FR-003,
 * FR-004, FR-006, FR-007). A null imputacion is always rendered as
 * "Sin imputar", never hidden.
 */
export function DetalleCompra({ idCompra }: { idCompra: number }) {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["compra", idCompra],
    queryFn: () => fetchCompraDetalle(idCompra),
  });

  if (isLoading) return <LoadingState />;

  if (isError) {
    const message = (error as Error)?.message ?? "";
    if (message.includes("404")) {
      return <EmptyState message="Compra no encontrada." />;
    }
    return (
      <ErrorState message="Ocurrió un error al cargar la compra." onRetry={() => refetch()} />
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-6">
      <Breadcrumb
        items={[{ label: "Compras", href: "/compras" }, { label: `Compra #${data.idCompra}` }]}
      />

      <section className="rounded-md border border-border bg-surface p-4">
        <h2 className="text-lg font-semibold text-ink-primary">Compra #{data.idCompra}</h2>
        <dl className="mt-2 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
          <div>
            <dt className="text-ink-secondary">Fecha</dt>
            <dd className="font-data">{data.fecha ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-ink-secondary">Proveedor</dt>
            <dd>
              <ContactoLink
                idContacto={data.proveedor?.idContacto}
                razonSocial={data.proveedor?.razonSocial}
                tipoContacto="Proveedor"
              />
            </dd>
          </div>
          <div>
            <dt className="text-ink-secondary">Tipo documento</dt>
            <dd>{data.tipoDocumento ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-ink-secondary">Nro. documento</dt>
            <dd className="font-data">{data.numeroDocumento ?? "—"}</dd>
          </div>
        </dl>
      </section>

      <section className="rounded-md border border-border bg-surface p-4">
        <h3 className="text-sm font-semibold text-ink-primary">
          Conceptos diferenciados (FR-007)
        </h3>
        <dl className="mt-2 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
          <div>
            <dt className="text-ink-secondary">Conceptos no gravados</dt>
            <dd className="font-data">{data.conceptosNoGravados ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-ink-secondary">Ingresos brutos</dt>
            <dd className="font-data">{data.ingresosBrutos ?? "—"}</dd>
          </div>
        </dl>
      </section>

      <section className="rounded-md border border-border bg-surface p-4">
        <h3 className="text-sm font-semibold text-ink-primary">Líneas de detalle</h3>
        <div className="mt-2 overflow-x-auto">
          <table className="min-w-full divide-y divide-border text-sm">
            <thead className="bg-surface-sunken text-left">
              <tr>
                <th className="px-3 py-1.5 font-medium text-ink-secondary">Producto/Servicio</th>
                <th className="px-3 py-1.5 font-medium text-ink-secondary">Cantidad</th>
                <th className="px-3 py-1.5 font-medium text-ink-secondary">Precio unitario</th>
                <th className="px-3 py-1.5 font-medium text-ink-secondary">IVA</th>
                <th className="px-3 py-1.5 font-medium text-ink-secondary">Imputación</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
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
    <tr className="align-top hover:bg-surface-sunken">
      <td className="px-3 py-1.5">{linea.productoServicio ?? "—"}</td>
      <td className="px-3 py-1.5 font-data">{linea.cantidad ?? "—"}</td>
      <td className="px-3 py-1.5 font-data">{linea.precioUnitario ?? "—"}</td>
      <td className="px-3 py-1.5 font-data">{linea.iva ?? "—"}</td>
      <td className="px-3 py-1.5">
        {linea.imputacion ? (
          <ul className="space-y-0.5">
            <li>Rubro: {linea.imputacion.rubro ?? "—"}</li>
            <li>
              Centro de costo:{" "}
              {linea.imputacion.centroCosto ?? (
                <span className="italic text-ink-muted">Sin asignar</span>
              )}
            </li>
            <li>
              Destino:{" "}
              {linea.imputacion.destino ?? (
                <span className="italic text-ink-muted">Sin asignar</span>
              )}
            </li>
            <li>
              Campaña:{" "}
              {linea.imputacion.campania ?? (
                <span className="italic text-ink-muted">Sin asignar</span>
              )}
            </li>
          </ul>
        ) : (
          <span className="italic text-ink-muted">Sin imputar</span>
        )}
      </td>
    </tr>
  );
}
