"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import {
  fetchFacturasCandidatas,
  vincularFactura,
  vincularRenglones,
  type FacturaCandidata,
  type LineaFactura,
  type RemitoDetalle,
  type RenglonRemito,
} from "@/services/remitosApi";
import { ApiError } from "@/services/apiClient";
import { formatCantidad, formatMoneda } from "@/lib/format";
import { NumberInput } from "@/components/ui/NumberInput";
import { SideDrawer } from "@/components/ui/SideDrawer";
import { useToast } from "@/components/ui/Toast";
import { filterInputClass } from "@/components/ui/FilterBar";

interface Eleccion {
  incluir: boolean;
  idDetalleRemito: number | null;
  cantidad: number | null;
}

const sel = `${filterInputClass} w-full px-1.5 py-0.5 text-xs`;

/** Palabras del nombre de un producto (4+ letras) para reconocerlo en la descripción de una factura. */
function tokensDe(nombre: string | null): string[] {
  return (nombre ?? "")
    .toUpperCase()
    .split(/[^A-Z0-9ÁÉÍÓÚÑ]+/)
    .filter((t) => t.length >= 4 && !/^\d+$/.test(t));
}

/**
 * Vinculación de un remito con facturas de Compras, renglón por renglón: qué renglón
 * de remito cubre qué renglón de factura y con qué cantidad. De ese vínculo sale el
 * costo de cada insumo (el remito no lleva precio), base de la imputación del costo
 * a cultivo y campaña. Se sugiere por producto cuando la factura ya lo tiene asignado.
 */
export function VinculacionPanel({
  remito,
  abierto,
  onClose,
  onChanged,
}: {
  remito: RemitoDetalle;
  abierto: boolean;
  onClose: () => void;
  onChanged: () => void;
}) {
  const { showToast } = useToast();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["facturas-candidatas", remito.idRemito],
    queryFn: () => fetchFacturasCandidatas(remito.idRemito),
    enabled: abierto,
    staleTime: 0,
    gcTime: 0,
  });
  const [elecciones, setElecciones] = useState<Record<number, Eleccion>>({});
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mostrarTodo, setMostrarTodo] = useState(false);

  const tokens = useMemo(() => new Map(remito.renglones.map((r) => [r.idDetalle, tokensDe(r.producto)])), [remito.renglones]);

  /** Renglones del remito que pueden corresponder a un renglón de factura. */
  function candidatosDe(l: LineaFactura): RenglonRemito[] {
    if (l.idProducto) return remito.renglones.filter((r) => r.idProducto === l.idProducto);
    const d = (l.descripcion ?? "").toUpperCase();
    const coinciden = remito.renglones.filter((r) => (tokens.get(r.idDetalle) ?? []).some((t) => d.includes(t)));
    return coinciden.length > 0 ? coinciden : mostrarTodo ? remito.renglones : [];
  }

  // Lo que le falta vincular a cada renglón del remito
  const faltante = useMemo(() => {
    const m = new Map<number, number>();
    remito.renglones.forEach((r) => m.set(r.idDetalle, Math.max(0, r.cantidad - r.cantidadVinculada)));
    return m;
  }, [remito]);

  // Sugerencia inicial: renglón de factura con el mismo producto que un renglón del remito con faltante
  useEffect(() => {
    if (!data) return;
    const restante = new Map(faltante);
    const inicial: Record<number, Eleccion> = {};
    data.forEach((f) =>
      f.lineas.forEach((l) => {
        const r = candidatosDe(l).find((x) => (restante.get(x.idDetalle) ?? 0) > 0.005);
        if (r && l.pendiente > 0.005) {
          const cant = Math.min(l.pendiente, restante.get(r.idDetalle) ?? 0);
          inicial[l.idDetalleCompra] = { incluir: false, idDetalleRemito: r.idDetalle, cantidad: Math.round(cant * 1000) / 1000 };
        }
      })
    );
    setElecciones(inicial);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, faltante, remito.renglones]);

  const ocultos = useMemo(() => {
    if (!data || mostrarTodo) return 0;
    return data.reduce((a, f) => a + f.lineas.filter((l) => candidatosDe(l).length === 0).length, 0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, mostrarTodo, tokens]);

  function cambiar(l: LineaFactura, cambios: Partial<Eleccion>) {
    setError(null);
    setElecciones((prev) => {
      const base: Eleccion = prev[l.idDetalleCompra] ?? { incluir: false, idDetalleRemito: null, cantidad: null };
      return { ...prev, [l.idDetalleCompra]: { ...base, ...cambios } };
    });
  }

  const seleccionadas = Object.entries(elecciones).filter(([, e]) => e.incluir && e.idDetalleRemito && e.cantidad && e.cantidad > 0);

  async function vincular() {
    setGuardando(true);
    setError(null);
    try {
      const res = await vincularRenglones(
        remito.idRemito,
        seleccionadas.map(([id, e]) => ({ idDetalleRemito: e.idDetalleRemito!, idDetalleCompra: Number(id), cantidad: e.cantidad! }))
      );
      showToast(res.advertencias.length ? `Vinculado. ${res.advertencias.join(" ")}` : "Renglones vinculados: ya hay costo para el stock.", res.advertencias.length ? "neutral" : "success");
      onChanged();
      onClose();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo vincular.");
    } finally {
      setGuardando(false);
    }
  }

  async function soloDocumento(f: FacturaCandidata) {
    try {
      await vincularFactura(remito.idRemito, f.idCompra);
      showToast("Factura vinculada al remito (sin detalle de renglones).", "success");
      onChanged();
      onClose();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo vincular la factura.");
    }
  }

  return (
    <SideDrawer open={abierto} onClose={onClose} title={`Vincular remito ${remito.nroRemito ?? ""} con facturas`} maxWidthClass="max-w-5xl">
      <p className="text-xs text-ink-secondary">
        Facturas de <strong>{remito.proveedor}</strong>, las más cercanas en fecha primero. Tildá cada renglón de factura que corresponda a un renglón de este remito y
        confirmá la cantidad. Un renglón se puede repartir en varios y viceversa.
      </p>
      {isLoading && <p className="mt-3 text-sm text-ink-secondary">Buscando facturas del proveedor…</p>}
      {isError && <p className="mt-3 text-sm text-status-danger">No se pudieron cargar las facturas.</p>}
      {data && data.length === 0 && <p className="mt-3 text-sm text-ink-secondary">Este proveedor no tiene facturas cargadas en Compras.</p>}
      {data && data.length > 0 && (
        <p className="mt-2 text-xs text-ink-secondary">
          {mostrarTodo ? "Se muestran todos los renglones." : `Se muestran los renglones que coinciden con los productos del remito (${ocultos} de otros productos ocultos).`}{" "}
          <button type="button" className="text-finance underline" onClick={() => setMostrarTodo((v) => !v)}>
            {mostrarTodo ? "Mostrar solo los que coinciden" : "Mostrar todos"}
          </button>
        </p>
      )}
      <div className="mt-3 space-y-3">
        {data?.filter((f) => f.lineas.some((l) => candidatosDe(l).length > 0)).map((f) => (
          <section key={f.idCompra} className="rounded-md border border-border bg-surface">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-3 py-2 text-xs">
              <span className="font-medium">
                {f.tipoDocumento} {f.numeroDocumento} · {f.fecha ?? "—"} · {f.moneda === "Dolares" ? "us$" : "$"}
                {f.vinculada && <span className="ml-2 rounded-sm bg-status-success-bg px-1.5 text-status-success">ya vinculada</span>}
              </span>
              {!f.vinculada && (
                <button type="button" className="text-finance underline" onClick={() => soloDocumento(f)}>
                  Vincular solo la factura (sin renglones)
                </button>
              )}
            </div>
            <table className="w-full text-xs">
              <thead className="text-left text-ink-secondary">
                <tr>
                  <th className="w-6" />
                  <th className="py-1 pr-2">Renglón de la factura</th>
                  <th className="pr-2 text-right">Cantidad</th>
                  <th className="pr-2 text-right">Precio</th>
                  <th className="pr-2 text-right">Ya remitido</th>
                  <th className="w-56 pr-2">Renglón del remito</th>
                  <th className="w-24 pr-2 text-right">Cantidad a vincular</th>
                </tr>
              </thead>
              <tbody>
                {f.lineas.filter((l) => candidatosDe(l).length > 0).map((l) => {
                  const e = elecciones[l.idDetalleCompra];
                  const compatibles = candidatosDe(l);
                  return (
                    <tr key={l.idDetalleCompra} className={`border-t border-border align-top ${e?.incluir ? "bg-finance-light" : ""}`}>
                      <td className="py-1 pl-2">
                        <input
                          type="checkbox"
                          checked={!!e?.incluir}
                          disabled={compatibles.length === 0}
                          onChange={(ev) => {
                            const primero = compatibles[0];
                            cambiar(l, {
                              incluir: ev.target.checked,
                              idDetalleRemito: e?.idDetalleRemito ?? primero?.idDetalle ?? null,
                              cantidad: e?.cantidad ?? Math.round(Math.min(Math.max(l.pendiente, 0), faltante.get(primero?.idDetalle ?? 0) ?? 0) * 1000) / 1000,
                            });
                          }}
                          aria-label={`Vincular ${l.descripcion}`}
                        />
                      </td>
                      <td className="py-1 pr-2">
                        {l.descripcion}
                        {!l.productoAsignado && <span className="ml-1 text-[11px] text-ink-secondary">(sin producto asignado: se le asignará el del remito)</span>}
                      </td>
                      <td className="pr-2 text-right font-data">{formatCantidad(l.cantidad)}</td>
                      <td className="pr-2 text-right font-data">{formatMoneda(l.precioUnitario, f.moneda === "Dolares" ? "Dolares" : "Pesos")}</td>
                      <td className="pr-2 text-right font-data">{formatCantidad(l.remitida)}</td>
                      <td className="pr-2 py-1">
                        <select
                          className={sel}
                          value={e?.idDetalleRemito ?? ""}
                          disabled={compatibles.length === 0}
                          onChange={(ev) => cambiar(l, { idDetalleRemito: ev.target.value ? Number(ev.target.value) : null })}
                        >
                          <option value="">{compatibles.length === 0 ? "Sin renglón del mismo producto" : "Elegir…"}</option>
                          {compatibles.map((r) => (
                            <option key={r.idDetalle} value={r.idDetalle}>
                              {r.producto} — falta vincular {formatCantidad(faltante.get(r.idDetalle) ?? 0)} {r.unidad}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="pr-2 py-1">
                        <NumberInput className={`${sel} text-right font-data`} value={e?.cantidad ?? null} onChange={(v) => cambiar(l, { cantidad: v })} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </section>
        ))}
      </div>
      <div className="sticky bottom-0 mt-4 flex items-center justify-between gap-3 border-t border-border bg-surface py-3">
        <span className="text-xs text-ink-secondary">{seleccionadas.length} renglón(es) elegidos</span>
        {error && <span className="text-xs text-status-danger">{error}</span>}
        <button
          type="button"
          disabled={seleccionadas.length === 0 || guardando}
          onClick={vincular}
          className="rounded-sm bg-finance px-4 py-2 text-sm text-white hover:opacity-90 disabled:opacity-40"
        >
          {guardando ? "Vinculando…" : `Vincular ${seleccionadas.length}`}
        </button>
      </div>
    </SideDrawer>
  );
}
