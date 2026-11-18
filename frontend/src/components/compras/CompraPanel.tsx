"use client";
import { useQuery } from "@tanstack/react-query";
import { LoadingState, ErrorState } from "@/components/ui/States";
import { formatCantidad, formatFecha, formatMoneda } from "@/lib/format";
import { fetchCompraDetalle } from "@/services/comprasApi";

/** Spec 051: resumen de una compra en el panel lateral (cabecera, renglones con su imputación y vencimientos). */
export function CompraPanel({ idCompra }: { idCompra: number }) {
  const { data: c, isLoading, isError, refetch } = useQuery({ queryKey: ["compra-panel", idCompra], queryFn: () => fetchCompraDetalle(idCompra) });
  if (isLoading) return <LoadingState rows={6} />;
  if (isError || !c) return <ErrorState message="No se pudo traer la compra." onRetry={() => refetch()} />;
  const moneda = c.moneda === "Dolares" ? "Dolares" : "Pesos";
  const neto = c.lineas.reduce((s, l) => s + (l.cantidad ?? 0) * (l.precioUnitario ?? 0), 0);
  const iva = c.lineas.reduce((s, l) => s + (l.cantidad ?? 0) * (l.precioUnitario ?? 0) * ((l.iva ?? 0) / 100), 0);
  return (
    <div className="space-y-4 text-sm">
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 rounded-lg bg-surface-sunken/60 p-3">
        <div><dt className="text-xs text-ink-secondary">Proveedor</dt><dd className="font-medium">{c.proveedor?.razonSocial ?? "—"}</dd></div>
        <div><dt className="text-xs text-ink-secondary">Fecha</dt><dd>{formatFecha(c.fecha)}</dd></div>
        <div><dt className="text-xs text-ink-secondary">Documento</dt><dd>{c.tipoDocumento ?? "—"} {c.tipo ?? ""} {c.numeroDocumento ?? ""}</dd></div>
        <div><dt className="text-xs text-ink-secondary">Moneda</dt><dd>{moneda === "Dolares" ? `Dólares${c.tipoDeCambio ? ` · TC ${formatCantidad(c.tipoDeCambio)}` : ""}` : "Pesos"}</dd></div>
      </dl>
      <div>
        <h3 className="mb-2 font-semibold text-ink-primary">Renglones</h3>
        <ul className="divide-y divide-border rounded-md border border-border">
          {c.lineas.map((l) => (
            <li key={l.idDetalleCompra} className="px-3 py-2">
              <div className="flex justify-between gap-3">
                <span className="min-w-0">{l.productoServicio ?? "—"}</span>
                <span className="font-data whitespace-nowrap">{formatMoneda((l.cantidad ?? 0) * (l.precioUnitario ?? 0), moneda)}</span>
              </div>
              <p className="text-xs text-ink-secondary">
                {formatCantidad(l.cantidad ?? 0)} × {formatMoneda(l.precioUnitario ?? 0, moneda)}
                {l.imputacion ? ` · ${[l.imputacion.rubro, l.imputacion.destino, l.imputacion.campania].filter(Boolean).join(" · ")}` : " · sin imputar"}
              </p>
            </li>
          ))}
        </ul>
        <div className="mt-2 space-y-0.5 text-right">
          <p className="text-ink-secondary">Neto <span className="font-data">{formatMoneda(neto, moneda)}</span> · IVA <span className="font-data">{formatMoneda(iva, moneda)}</span></p>
        </div>
      </div>
      {c.vencimientos.length > 0 && (
        <div>
          <h3 className="mb-1 font-semibold text-ink-primary">Vencimientos</h3>
          <ul className="text-ink-secondary">{c.vencimientos.map((v) => <li key={v.idVencimiento}>{formatFecha(v.fechaVencimiento)}{v.importe ? ` · ${formatMoneda(v.importe, moneda)}` : ""}</li>)}</ul>
        </div>
      )}
    </div>
  );
}
