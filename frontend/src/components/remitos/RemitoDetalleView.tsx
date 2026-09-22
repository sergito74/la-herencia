"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import {
  anularRemito,
  desvincularFactura,
  desvincularRenglon,
  fetchCatalogosRemitos,
  fetchRemito,
} from "@/services/remitosApi";
import { ApiError } from "@/services/apiClient";
import { urlDocumentoLocal } from "@/services/comprasApi";
import { urlParaAbrirDocumento } from "@/lib/documentoLocal";
import { formatCantidad, formatMoneda } from "@/lib/format";
import { filterInputClass } from "@/components/ui/FilterBar";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useToast } from "@/components/ui/Toast";
import { BadgeFactura, BadgeRenglones } from "@/components/remitos/EstadosRemito";
import { VinculacionPanel } from "@/components/remitos/VinculacionPanel";

/** Detalle de un remito: renglones con su estado de vinculación, costo FIFO y consumo. */
export function RemitoDetalleView({ idRemito }: { idRemito: number }) {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["remito", idRemito], queryFn: () => fetchRemito(idRemito), staleTime: 0 });
  const { data: catalogos } = useQuery({ queryKey: ["catalogos-remitos"], queryFn: fetchCatalogosRemitos, staleTime: Infinity });
  const [vinculando, setVinculando] = useState(false);
  const [anulando, setAnulando] = useState(false);
  const [motivo, setMotivo] = useState("");
  const [error, setError] = useState<string | null>(null);

  function refrescar() {
    refetch();
    qc.invalidateQueries({ queryKey: ["remitos"] });
    qc.invalidateQueries({ queryKey: ["existencias"] });
  }

  async function quitarVinculo(idVinculo: number) {
    try {
      await desvincularRenglon(idRemito, idVinculo);
      showToast("Vínculo quitado.", "success");
      refrescar();
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "No se pudo quitar el vínculo.", "danger");
    }
  }

  async function quitarFactura(idCompra: number) {
    try {
      await desvincularFactura(idRemito, idCompra);
      showToast("Factura desvinculada (y sus renglones).", "success");
      refrescar();
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "No se pudo desvincular la factura.", "danger");
    }
  }

  async function anular() {
    setError(null);
    try {
      await anularRemito(idRemito, motivo);
      showToast("Remito anulado: su entrada salió del stock.", "success");
      setAnulando(false);
      refrescar();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo anular el remito.");
    }
  }

  if (isLoading) return <LoadingState />;
  if (isError || !data) return <ErrorState message="No se pudo cargar el remito." onRetry={() => refetch()} />;
  const establecimiento = catalogos?.establecimientos.find((e) => e.id === data.idEstablecimiento)?.nombre;
  const urlArchivo = data.archivo ? urlParaAbrirDocumento(data.archivo, "", urlDocumentoLocal) : null;

  return (
    <div className="space-y-4">
      {data.anulado && (
        <div className="rounded-md border border-status-danger bg-status-danger-bg p-3 text-sm text-status-danger">
          Remito anulado — {data.motivoAnulacion}. Su entrada no suma al stock.
        </div>
      )}
      <div className="flex flex-wrap items-start justify-between gap-3 rounded-md border border-border bg-surface p-4">
        <div className="space-y-1 text-sm">
          <div className="text-lg font-semibold">
            Remito {data.nroRemito} <span className="text-sm font-normal text-ink-secondary">· {data.fecha}</span>
          </div>
          <div>{data.proveedor}</div>
          <div className="flex flex-wrap items-center gap-2 text-xs text-ink-secondary">
            {establecimiento && <span>{establecimiento}</span>}
            <BadgeFactura estado={data.estadoFactura} />
            <BadgeRenglones estado={data.estadoRenglones} />
            {data.revisarDuplicado && <StatusBadge label="Duplicado a revisar" tone="warning" />}
          </div>
          {data.observaciones && <div className="text-xs text-ink-secondary">{data.observaciones}</div>}
          {urlArchivo && (
            <a href={urlArchivo} target="_blank" rel="noreferrer" className="text-xs text-finance underline">
              Abrir foto o PDF del remito
            </a>
          )}
        </div>
        {!data.anulado && (
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={() => setVinculando(true)} className="rounded-sm bg-finance px-4 py-2 text-sm text-white hover:opacity-90">
              Vincular con facturas
            </button>
            <Link href={`/produccion/remitos/${idRemito}/editar`} className="rounded-sm border border-finance px-4 py-2 text-sm text-finance hover:bg-finance-light">
              Editar
            </Link>
            <button type="button" onClick={() => setAnulando(true)} className="rounded-sm border border-border px-4 py-2 text-sm text-status-danger hover:bg-surface-sunken">
              Anular
            </button>
          </div>
        )}
      </div>

      {anulando && (
        <div className="rounded-md border border-border bg-surface-sunken p-3">
          <p className="text-sm font-medium">¿Por qué se anula este remito?</p>
          <input className={`${filterInputClass} mt-2 w-full`} value={motivo} onChange={(e) => setMotivo(e.target.value)} placeholder="Motivo de la anulación" />
          {error && <p className="mt-1 text-xs text-status-danger">{error}</p>}
          <div className="mt-2 flex gap-2">
            <button type="button" disabled={!motivo.trim()} onClick={anular} className="rounded-sm bg-status-danger px-3 py-1 text-sm text-white disabled:opacity-40">
              Anular remito
            </button>
            <button type="button" onClick={() => setAnulando(false)} className="rounded-sm border border-border px-3 py-1 text-sm">
              Cancelar
            </button>
          </div>
        </div>
      )}

      <div className="rounded-md border border-border bg-surface p-4">
        <h2 className="text-sm font-medium">Renglones</h2>
        <table className="mt-2 w-full text-xs">
          <thead className="text-left text-ink-secondary">
            <tr>
              <th className="py-1 pr-2">Producto</th>
              <th className="pr-2 text-right">Cantidad</th>
              <th className="pr-2">Vencimiento</th>
              <th className="pr-2 text-right">Vinculado</th>
              <th className="pr-2">Estado</th>
              <th className="pr-2 text-right">Costo unitario</th>
              <th className="text-right">Consumido</th>
            </tr>
          </thead>
          <tbody>
            {data.renglones.map((r) => (
              <>
                <tr key={r.idDetalle} className="border-t border-border align-top">
                  <td className="py-1 pr-2">
                    {r.producto} <span className="text-ink-secondary">· {r.tipo}</span>
                    {r.equivalenciaPendiente && <div className="text-[11px] text-status-warning">Falta la equivalencia de {r.unidad} a {r.unidadBase}: el stock lo cuenta 1 a 1.</div>}
                  </td>
                  <td className="pr-2 text-right font-data">
                    {formatCantidad(r.cantidad)} {r.unidad}
                    {r.unidadBase && r.unidad !== r.unidadBase && <div className="text-[11px] text-ink-secondary">= {formatCantidad(r.cantidad * r.factorABase)} {r.unidadBase}</div>}
                  </td>
                  <td className="pr-2">{r.vencimiento ?? "—"}</td>
                  <td className="pr-2 text-right font-data">{formatCantidad(r.cantidadVinculada)}</td>
                  <td className="pr-2">
                    <BadgeRenglones estado={r.estadoVinculo} />
                  </td>
                  <td className="pr-2 text-right font-data">{r.costoUnitario != null ? formatMoneda(r.costoUnitario) : <span className="text-ink-secondary">pendiente</span>}</td>
                  <td className="text-right font-data">{r.consumido > 0 ? formatCantidad(r.consumido) : "—"}</td>
                </tr>
                {r.vinculos.map((v) => (
                  <tr key={`v${v.idVinculo}`} className="text-ink-secondary">
                    <td className="pb-1 pl-4 pr-2" colSpan={6}>
                      ↳ {v.tipoDocumento} {v.numeroDocumento} · {v.descripcion} · {formatCantidad(v.cantidad)} de {formatCantidad(v.cantidadCompra)} a{" "}
                      {formatMoneda(v.precioUnitario, v.moneda === "Dolares" ? "Dolares" : "Pesos")}
                    </td>
                    <td className="pb-1 text-right">
                      {!data.anulado && (
                        <button type="button" className="hover:text-status-danger" title="Quitar vínculo" onClick={() => quitarVinculo(v.idVinculo)}>
                          ✕
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </>
            ))}
          </tbody>
        </table>
      </div>

      <div className="rounded-md border border-border bg-surface p-4">
        <h2 className="text-sm font-medium">Facturas vinculadas</h2>
        {data.facturas.length === 0 ? (
          <p className="mt-1 text-xs text-ink-secondary">Este remito todavía no tiene factura. Los productos ya suman al stock, con costo pendiente hasta vincular la factura.</p>
        ) : (
          <ul className="mt-1 space-y-1 text-xs">
            {data.facturas.map((f) => (
              <li key={f.idCompra} className="flex items-center gap-2">
                <Link className="text-finance underline" href={`/compras/${f.idCompra}`}>
                  {f.tipoDocumento} {f.numeroDocumento}
                </Link>
                <span className="text-ink-secondary">{f.fecha}</span>
                {!data.anulado && (
                  <button type="button" className="text-ink-secondary hover:text-status-danger" title="Desvincular la factura y sus renglones" onClick={() => quitarFactura(f.idCompra)}>
                    ✕
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      <VinculacionPanel remito={data} abierto={vinculando} onClose={() => setVinculando(false)} onChanged={refrescar} />
    </div>
  );
}
