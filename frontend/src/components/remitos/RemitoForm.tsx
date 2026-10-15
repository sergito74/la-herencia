"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import {
  actualizarRemito,
  crearRemito,
  fetchCatalogosRemitos,
  fetchProducto,
  fetchRemito,
  fetchUnidades,
  validarRemito,
  type Producto,
  type RemitoInput,
} from "@/services/remitosApi";
import { ApiError } from "@/services/apiClient";
import { formatCantidad } from "@/lib/format";
import { ArchivoVinculado } from "@/components/ui/ArchivoVinculado";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { filterInputClass } from "@/components/ui/FilterBar";
import { NumberInput } from "@/components/ui/NumberInput";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { useToast } from "@/components/ui/Toast";
import { ProductoSelect } from "@/components/remitos/ProductoSelect";

interface Renglon {
  clave: string;
  idDetalle: number | null;
  producto: { idProducto: number; producto: string } | null;
  info: Producto | null;
  cantidad: number | null;
  unidad: string;
  vencimiento: string;
  unidadBase: string;
  factorUnidad: number | null;
  /** Solo en edición: por qué el renglón está congelado. */
  congelado: { motivo: "consumo" | "factura"; consumido: number; vinculado: boolean } | null;
}

const FILAS_INICIALES = 10;
const input = `${filterInputClass} w-full px-1.5 py-1 text-xs`;
const labelCompacto = "flex flex-col gap-0.5 text-xs text-ink-secondary";
// Celda de la grilla, igual que la de Compras (ComprasGrid): sin borde, resalta al enfocar.
const celda = "w-full border-0 bg-transparent px-1.5 py-0.5 text-xs text-ink-primary focus:bg-finance-light focus:outline-none disabled:cursor-not-allowed disabled:opacity-60";
let contador = 0;
const nuevaClave = () => `r${++contador}`;
const vacio = (): Renglon => ({
  clave: nuevaClave(), idDetalle: null, producto: null, info: null, cantidad: null, unidad: "LTS", vencimiento: "", unidadBase: "", factorUnidad: null, congelado: null,
});
const hoy = () => new Date().toISOString().slice(0, 10);
const rellenar = (filas: Renglon[]) => [...filas, ...Array.from({ length: Math.max(0, FILAS_INICIALES - filas.length) }, vacio)];

/**
 * Alta y edición de un remito (010). El remito suma stock al guardarse; no lleva precio.
 * Mismo formato que la carga de Compras: encabezado y pie fijos, grilla tipo planilla
 * con filas vacías en el medio (la única parte que scrollea).
 */
export function RemitoForm({ idRemito }: { idRemito?: number }) {
  const edicion = idRemito != null;
  const router = useRouter();
  const search = useSearchParams();
  const { showToast } = useToast();

  const [fecha, setFecha] = useState(hoy());
  const [idProveedor, setIdProveedor] = useState<number | null>(null);
  const [proveedor, setProveedor] = useState<string | null>(null);
  const [nro, setNro] = useState("");
  const [idEstablecimiento, setIdEstablecimiento] = useState<number | "">("");
  const [observaciones, setObservaciones] = useState("");
  const [archivo, setArchivo] = useState("");
  const [renglones, setRenglones] = useState<Renglon[]>(() => rellenar([]));
  const [advertencias, setAdvertencias] = useState<string[]>([]);
  const [confirmado, setConfirmado] = useState(false);
  const [confirmacionServidor, setConfirmacionServidor] = useState<string[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  const cargado = useRef(false);

  const { data: unidades } = useQuery({ queryKey: ["unidades"], queryFn: fetchUnidades, staleTime: Infinity });
  const { data: catalogos } = useQuery({ queryKey: ["catalogos-remitos"], queryFn: fetchCatalogosRemitos, staleTime: Infinity });
  const remitoQuery = useQuery({ queryKey: ["remito", idRemito], queryFn: () => fetchRemito(idRemito!), enabled: edicion, staleTime: 0, gcTime: 0 });

  // Precarga desde "Facturas sin remito" (?idProveedor=&proveedor=)
  useEffect(() => {
    if (edicion) return;
    const id = Number(search.get("idProveedor"));
    if (id > 0) {
      setIdProveedor(id);
      setProveedor(search.get("proveedor"));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!edicion || cargado.current || !remitoQuery.data) return;
    cargado.current = true;
    const r = remitoQuery.data;
    setFecha(r.fecha ?? hoy());
    setIdProveedor(r.idProveedor);
    setProveedor(r.proveedor);
    setNro(r.nroRemito ?? "");
    setIdEstablecimiento(r.idEstablecimiento ?? "");
    setObservaciones(r.observaciones ?? "");
    setArchivo(r.archivo ?? "");
    setRenglones(rellenar(
      r.renglones.map((l) => ({
        clave: nuevaClave(),
        idDetalle: l.idDetalle,
        producto: { idProducto: l.idProducto, producto: l.producto ?? `Producto ${l.idProducto}` },
        info: null,
        cantidad: l.cantidad,
        unidad: l.unidad,
        vencimiento: l.vencimiento ?? "",
        unidadBase: l.unidadBase ?? "",
        factorUnidad: null,
        congelado: l.congelado ? { motivo: l.motivoCongelado ?? "consumo", consumido: l.consumido, vinculado: l.vinculos.length > 0 } : null,
      }))
    ));
  }, [edicion, remitoQuery.data]);

  // Información de cada producto elegido (unidad base y equivalencias)
  useEffect(() => {
    renglones.forEach((r) => {
      if (r.producto && (!r.info || r.info.idProducto !== r.producto.idProducto)) {
        fetchProducto(r.producto.idProducto)
          .then((info) =>
            setRenglones((prev) =>
              prev.map((x) =>
                x.clave === r.clave
                  ? { ...x, info, unidad: x.unidad || info.unidadBase || info.unidadBaseSugerida || "LTS", unidadBase: info.unidadBase ?? x.unidadBase }
                  : x
              )
            )
          )
          .catch(() => undefined);
      }
    });
  }, [renglones]);

  // Advertencias del número de remito (formato / duplicado)
  useEffect(() => {
    if (!idProveedor || !nro.trim()) {
      setAdvertencias([]);
      return;
    }
    const t = setTimeout(() => {
      validarRemito(idProveedor, nro.trim(), idRemito)
        .then((r) => {
          setAdvertencias(r.mensajes);
          if (r.mensajes.length === 0) setConfirmado(false);
        })
        .catch(() => setAdvertencias([]));
    }, 400);
    return () => clearTimeout(t);
  }, [idProveedor, nro, idRemito]);

  const unidadesBase = useMemo(() => (unidades ?? []).filter((u) => u.esBase), [unidades]);
  const sinRemito = nro.trim().toUpperCase() === "SIN REMITO";

  function actualizar(clave: string, cambios: Partial<Renglon>) {
    setError(null);
    setRenglones((prev) => prev.map((r) => (r.clave === clave ? { ...r, ...cambios } : r)));
  }

  function baseDe(r: Renglon): string {
    return r.info?.unidadBase ?? (r.unidadBase || r.info?.unidadBaseSugerida || "LTS");
  }

  function necesitaEquivalencia(r: Renglon): boolean {
    if (!r.info || !r.unidad || r.unidad === baseDe(r)) return false;
    return !r.info.equivalencias?.some((e) => e.unidad === r.unidad);
  }

  async function guardar(confirmar: boolean) {
    setError(null);
    if (!idProveedor) return setError("Elegí el proveedor.");
    if (!nro.trim()) return setError("Indicá el número de remito (o tildá «Sin remito»).");
    const validos = renglones.filter((r) => r.producto || r.cantidad);
    if (validos.length === 0) return setError("Cargá al menos un renglón.");
    for (const [i, r] of validos.entries()) {
      if (!r.producto) return setError(`Renglón ${i + 1}: elegí el producto.`);
      if (!r.cantidad || r.cantidad <= 0) return setError(`Renglón ${i + 1}: la cantidad debe ser mayor a cero.`);
      if (necesitaEquivalencia(r) && !r.factorUnidad) return setError(`Renglón ${i + 1}: indicá cuántos ${baseDe(r)} tiene 1 ${r.unidad}.`);
    }
    const body: RemitoInput = {
      fecha,
      idProveedor,
      nroRemito: nro.trim(),
      idEstablecimiento: idEstablecimiento === "" ? null : idEstablecimiento,
      observaciones: observaciones.trim() || null,
      archivo: archivo.trim() || null,
      confirmar,
      renglones: validos.map((r) => ({
        idDetalle: r.idDetalle,
        idProducto: r.producto!.idProducto,
        cantidad: r.cantidad!,
        unidad: r.unidad,
        vencimiento: r.vencimiento || null,
        unidadBase: r.info?.unidadBase ? null : baseDe(r),
        factorUnidad: necesitaEquivalencia(r) ? r.factorUnidad : null,
      })),
    };
    setGuardando(true);
    try {
      const res = edicion ? await actualizarRemito(idRemito!, body) : await crearRemito(body);
      showToast(edicion ? "Remito actualizado." : "Remito guardado: el stock ya suma sus productos.", "success");
      router.push(`/produccion/remitos/${res.idRemito}`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) setConfirmacionServidor(e.message.split(/(?<=\.)\s+/));
      else setError(e instanceof ApiError ? e.message : "No se pudo guardar el remito.");
    } finally {
      setGuardando(false);
    }
  }

  if (edicion && remitoQuery.isLoading) return <LoadingState />;
  if (edicion && (remitoQuery.isError || !remitoQuery.data)) return <ErrorState message="No se pudo cargar el remito." onRetry={() => remitoQuery.refetch()} />;
  if (edicion && remitoQuery.data?.anulado) return <p className="text-sm text-status-danger">El remito está anulado: no se puede editar.</p>;

  const hayCongelados = renglones.some((r) => r.congelado);

  const filaIniciada = (r: Renglon) => !!(r.producto || r.cantidad);

  return (
    <form
      className="flex flex-col gap-2"
      style={{ height: "calc(100vh - 8rem)" }}
      onSubmit={(e) => {
        e.preventDefault();
        guardar(confirmado);
      }}
      suppressHydrationWarning
    >
      {/* Encabezado fijo, como Compras: los campos se reparten por todo el ancho. */}
      <div className="shrink-0 space-y-2">
      <div className="grid grid-cols-[repeat(auto-fit,minmax(10rem,1fr))] items-end gap-2 rounded-md border border-border bg-surface p-2">
        <div className={`${labelCompacto} sm:col-span-2`}>
          Proveedor
          <ContactoSelect
            value={idProveedor}
            razonSocial={proveedor}
            tipoContacto={["Proveedor", "Multiple"]}
            onChange={(id, nombre) => {
              setIdProveedor(id);
              setProveedor(nombre);
            }}
            placeholder="Buscar proveedor…"
          />
          {hayCongelados && <span className="text-[11px]">No se puede cambiar: hay renglones consumidos o vinculados a una factura.</span>}
        </div>
        <label className={labelCompacto}>
          Fecha
          <input type="date" required className={input} value={fecha} disabled={hayCongelados} onChange={(e) => setFecha(e.target.value)} />
        </label>
        <label className={labelCompacto}>
          N° de remito
          <input className={input} value={nro} onChange={(e) => setNro(e.target.value)} placeholder="0000-00000000" disabled={sinRemito} />
        </label>
        <label className="flex items-center gap-1.5 self-center text-xs text-ink-secondary">
          <input type="checkbox" checked={sinRemito} onChange={(e) => setNro(e.target.checked ? "SIN REMITO" : "")} />
          Entregó sin remito
        </label>
        <label className={labelCompacto}>
          Establecimiento
          <select className={input} value={idEstablecimiento} onChange={(e) => setIdEstablecimiento(e.target.value ? Number(e.target.value) : "")}>
            <option value="">—</option>
            {catalogos?.establecimientos.map((e) => (
              <option key={e.id} value={e.id}>
                {e.nombre}
              </option>
            ))}
          </select>
        </label>
        <label className={`${labelCompacto} sm:col-span-2`}>
          Observaciones
          <input className={input} value={observaciones} onChange={(e) => setObservaciones(e.target.value)} maxLength={500} />
        </label>
        <ArchivoVinculado className="sm:col-span-2" label="Foto o PDF del remito (opcional)" value={archivo} onChange={setArchivo} inputClassName={input} />
      </div>

      {advertencias.length > 0 && (
        <div className="rounded-md border border-status-warning bg-status-warning-bg px-2 py-1 text-xs">
          <ul className="list-disc pl-4">
            {advertencias.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
          <label className="mt-1 flex items-center gap-2 font-medium">
            <input type="checkbox" checked={confirmado} onChange={(e) => setConfirmado(e.target.checked)} />
            Es correcto, guardar igual
          </label>
        </div>
      )}
      </div>

      {/* Cuerpo: única sección que scrollea. */}
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="rounded-md border border-border">
        <table className="min-w-full divide-y divide-border text-xs">
          <thead className="sticky top-0 z-10 bg-surface-sunken text-left">
            <tr>
              {["Cantidad", "Unidad", "Producto", "Tipo · principio activo", "Unidad base / equivalencia", "Vencimiento", "Notas", ""].map((h) => (
                <th key={h} className="whitespace-nowrap px-1.5 py-1 font-medium text-ink-secondary">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {renglones.map((r) => {
              const congelado = r.congelado;
              const sinBase = r.info && !r.info.unidadBase;
              return (
                <tr key={r.clave} className="align-top hover:bg-surface-sunken">
                  <td className="w-24">
                    <NumberInput className={`${celda} text-right font-data`} value={r.cantidad} onChange={(v) => actualizar(r.clave, { cantidad: v })} disabled={!!congelado?.vinculado} />
                  </td>
                  <td className="w-24">
                    <select className={`${celda} cursor-pointer`} value={r.unidad} disabled={!!congelado} onChange={(e) => actualizar(r.clave, { unidad: e.target.value, factorUnidad: null })}>
                      {(unidades ?? []).map((u) => (
                        <option key={u.codigo} value={u.codigo}>
                          {u.codigo}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="min-w-[18rem]">
                    <ProductoSelect
                      value={r.producto}
                      disabled={!!congelado}
                      inputClassName={celda}
                      placeholder=""
                      onChange={(p) => actualizar(r.clave, { producto: { idProducto: p.idProducto, producto: p.producto }, info: p, unidad: p.unidadBase ?? p.unidadBaseSugerida ?? "LTS", unidadBase: p.unidadBase ?? "", factorUnidad: null })}
                    />
                  </td>
                  <td className="min-w-[12rem] px-1.5 py-0.5 text-ink-secondary">
                    {r.info && [r.info.tipo, r.info.ingredienteActivo].filter(Boolean).join(" · ")}
                  </td>
                  <td className="min-w-[11rem] px-1.5 py-0.5 text-ink-secondary">
                    {r.info && !sinBase && !necesitaEquivalencia(r) && r.info.unidadBase}
                    {sinBase && (
                      <label className="flex items-center gap-1">
                        Base
                        <select className={`${celda} cursor-pointer`} value={baseDe(r)} onChange={(e) => actualizar(r.clave, { unidadBase: e.target.value })}>
                          {unidadesBase.map((u) => (
                            <option key={u.codigo} value={u.codigo}>
                              {u.codigo}
                            </option>
                          ))}
                        </select>
                      </label>
                    )}
                    {necesitaEquivalencia(r) && (
                      <label className="flex items-center gap-1 whitespace-nowrap">
                        1 {r.unidad} =
                        <NumberInput className={`${celda} w-16 text-right font-data`} value={r.factorUnidad} onChange={(v) => actualizar(r.clave, { factorUnidad: v })} />
                        {baseDe(r)}
                      </label>
                    )}
                  </td>
                  <td className="w-32">
                    <input type="date" className={celda} value={r.vencimiento} onChange={(e) => actualizar(r.clave, { vencimiento: e.target.value })} />
                  </td>
                  <td className="px-1.5 py-0.5 text-[11px] text-ink-secondary">
                    {congelado && (
                      <span>
                        {congelado.consumido > 0 && `Ya se consumieron ${formatCantidad(congelado.consumido)}. `}
                        {congelado.vinculado && "Vinculado a una factura: la cantidad no se puede cambiar. "}
                        No se puede quitar ni cambiar el producto.
                      </span>
                    )}
                  </td>
                  <td className="w-6 px-1 text-center">
                    {!congelado && filaIniciada(r) && (
                      <button type="button" className="text-ink-secondary hover:text-status-danger" title="Eliminar renglón" aria-label="Eliminar renglón" onClick={() => setRenglones((p) => rellenar(p.filter((x) => x.clave !== r.clave)))}>
                        ✕
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <button type="button" className="m-1.5 text-xs text-finance underline" onClick={() => setRenglones((p) => [...p, ...Array.from({ length: 5 }, vacio)])}>
          + Agregar 5 renglones
        </button>
        </div>
      </div>

      {/* Pie fijo, como Compras. */}
      <div className="shrink-0 space-y-2">
        {confirmacionServidor && (
          <div className="rounded-md border border-status-warning bg-status-warning-bg px-2 py-1 text-xs">
            <ul className="list-disc pl-4">
              {confirmacionServidor.map((m) => (
                <li key={m}>{m}</li>
              ))}
            </ul>
            <div className="mt-1 flex gap-2">
              <button type="button" className="rounded-sm bg-finance px-3 py-1 text-white" disabled={guardando} onClick={() => { setConfirmacionServidor(null); guardar(true); }}>
                Confirmar y guardar
              </button>
              <button type="button" className="rounded-sm border border-border px-3 py-1" onClick={() => setConfirmacionServidor(null)}>
                Volver
              </button>
            </div>
          </div>
        )}
        <div className="flex items-center justify-between gap-2 rounded-md border border-border bg-surface-sunken p-2 text-xs">
          <span className="text-ink-secondary">
            {edicion
              ? "Los renglones consumidos o vinculados a una factura quedan congelados; para corregirlos, anular el remito y cargar uno nuevo. "
              : "Al guardar, los productos suman al stock. El costo sale de la factura que se vincule después. "}
            Renglones cargados: <span className="font-data text-ink-primary">{renglones.filter(filaIniciada).length}</span>
            {error && <span className="ml-3 text-status-danger">{error}</span>}
          </span>
          <div className="flex gap-2">
            <button type="button" onClick={() => router.back()} className="rounded-sm border border-border px-3 py-1.5 text-xs text-ink-secondary hover:text-ink-primary">
              Cancelar
            </button>
            <button type="submit" disabled={guardando} className="rounded-sm bg-finance px-3 py-1.5 text-xs text-white hover:opacity-90 disabled:opacity-40">
              {guardando ? "Guardando…" : edicion ? "Guardar cambios" : "Guardar remito"}
            </button>
          </div>
        </div>
      </div>
    </form>
  );
}
