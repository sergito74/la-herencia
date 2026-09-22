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

const input = `${filterInputClass} w-full px-1.5 py-1 text-xs`;
let contador = 0;
const nuevaClave = () => `r${++contador}`;
const vacio = (): Renglon => ({
  clave: nuevaClave(), idDetalle: null, producto: null, info: null, cantidad: null, unidad: "LTS", vencimiento: "", unidadBase: "", factorUnidad: null, congelado: null,
});
const hoy = () => new Date().toISOString().slice(0, 10);

/** Alta y edición de un remito (010). El remito suma stock al guardarse; no lleva precio. */
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
  const [renglones, setRenglones] = useState<Renglon[]>([vacio()]);
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
    setRenglones(
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
    );
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

  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        guardar(confirmado);
      }}
    >
      <div className="grid gap-3 rounded-md border border-border bg-surface p-4 sm:grid-cols-2 lg:grid-cols-4">
        <label className="text-xs text-ink-secondary">
          Fecha
          <input type="date" required className={input} value={fecha} disabled={hayCongelados} onChange={(e) => setFecha(e.target.value)} />
        </label>
        <div className="text-xs text-ink-secondary sm:col-span-1 lg:col-span-2">
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
        <label className="text-xs text-ink-secondary">
          N° de remito
          <input className={input} value={nro} onChange={(e) => setNro(e.target.value)} placeholder="0000-00000000" disabled={sinRemito} />
          <span className="mt-1 flex items-center gap-1">
            <input type="checkbox" checked={sinRemito} onChange={(e) => setNro(e.target.checked ? "SIN REMITO" : "")} />
            El proveedor entregó sin remito
          </span>
        </label>
        <label className="text-xs text-ink-secondary">
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
        <label className="text-xs text-ink-secondary sm:col-span-2 lg:col-span-3">
          Observaciones
          <input className={input} value={observaciones} onChange={(e) => setObservaciones(e.target.value)} maxLength={500} />
        </label>
        <ArchivoVinculado className="sm:col-span-2 lg:col-span-4" label="Foto o PDF del remito (opcional)" value={archivo} onChange={setArchivo} inputClassName={input} />
      </div>

      {advertencias.length > 0 && (
        <div className="rounded-md border border-status-warning bg-status-warning-bg p-3 text-xs">
          <ul className="list-disc pl-4">
            {advertencias.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
          <label className="mt-2 flex items-center gap-2 font-medium">
            <input type="checkbox" checked={confirmado} onChange={(e) => setConfirmado(e.target.checked)} />
            Es correcto, guardar igual
          </label>
        </div>
      )}

      <div className="rounded-md border border-border bg-surface p-4">
        <h2 className="text-sm font-medium">Renglones</h2>
        <div className="mt-2 overflow-visible">
          <table className="w-full text-xs">
            <thead className="text-left text-ink-secondary">
              <tr>
                <th className="w-[36%] py-1 pr-2">Producto</th>
                <th className="w-24 pr-2">Cantidad</th>
                <th className="w-28 pr-2">Unidad</th>
                <th className="w-36 pr-2">Vencimiento (opcional)</th>
                <th className="pr-2">Notas</th>
                <th className="w-6" />
              </tr>
            </thead>
            <tbody>
              {renglones.map((r) => {
                const congelado = r.congelado;
                const sinBase = r.info && !r.info.unidadBase;
                return (
                  <tr key={r.clave} className="border-t border-border align-top">
                    <td className="py-1 pr-2">
                      <ProductoSelect
                        value={r.producto}
                        disabled={!!congelado}
                        onChange={(p) => actualizar(r.clave, { producto: { idProducto: p.idProducto, producto: p.producto }, info: p, unidad: p.unidadBase ?? p.unidadBaseSugerida ?? "LTS", unidadBase: p.unidadBase ?? "", factorUnidad: null })}
                      />
                      {r.info && (
                        <span className="text-[11px] text-ink-secondary">
                          {r.info.tipo ?? "—"} · unidad base {r.info.unidadBase ?? `(a definir: ${r.info.unidadBaseSugerida})`}
                        </span>
                      )}
                    </td>
                    <td className="py-1 pr-2">
                      <NumberInput
                        className={`${input} text-right font-data`}
                        value={r.cantidad}
                        onChange={(v) => actualizar(r.clave, { cantidad: v })}
                        disabled={!!congelado?.vinculado}
                      />
                    </td>
                    <td className="py-1 pr-2">
                      <select className={input} value={r.unidad} disabled={!!congelado} onChange={(e) => actualizar(r.clave, { unidad: e.target.value, factorUnidad: null })}>
                        {(unidades ?? []).map((u) => (
                          <option key={u.codigo} value={u.codigo}>
                            {u.codigo}
                          </option>
                        ))}
                      </select>
                      {sinBase && (
                        <label className="mt-1 block text-[11px] text-ink-secondary">
                          Unidad base del producto
                          <select className={input} value={baseDe(r)} onChange={(e) => actualizar(r.clave, { unidadBase: e.target.value })}>
                            {unidadesBase.map((u) => (
                              <option key={u.codigo} value={u.codigo}>
                                {u.codigo}
                              </option>
                            ))}
                          </select>
                        </label>
                      )}
                      {necesitaEquivalencia(r) && (
                        <label className="mt-1 block text-[11px] text-ink-secondary">
                          1 {r.unidad} = ¿cuántos {baseDe(r)}?
                          <NumberInput className={`${input} text-right font-data`} value={r.factorUnidad} onChange={(v) => actualizar(r.clave, { factorUnidad: v })} />
                        </label>
                      )}
                    </td>
                    <td className="py-1 pr-2">
                      <input type="date" className={input} value={r.vencimiento} onChange={(e) => actualizar(r.clave, { vencimiento: e.target.value })} />
                    </td>
                    <td className="py-1 pr-2 text-[11px] text-ink-secondary">
                      {congelado && (
                        <span>
                          {congelado.consumido > 0 && `Ya se consumieron ${formatCantidad(congelado.consumido)}. `}
                          {congelado.vinculado && "Vinculado a una factura: la cantidad no se puede cambiar. "}
                          No se puede quitar ni cambiar el producto.
                        </span>
                      )}
                    </td>
                    <td className="py-1">
                      {!congelado && renglones.length > 1 && (
                        <button type="button" className="text-ink-secondary hover:text-status-danger" title="Quitar renglón" onClick={() => setRenglones((p) => p.filter((x) => x.clave !== r.clave))}>
                          ✕
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <button type="button" className="mt-2 text-xs text-finance underline" onClick={() => setRenglones((p) => [...p, vacio()])}>
          + Agregar renglón
        </button>
      </div>

      {confirmacionServidor && (
        <div className="rounded-md border border-status-warning bg-status-warning-bg p-3 text-xs">
          <ul className="list-disc pl-4">
            {confirmacionServidor.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
          <div className="mt-2 flex gap-2">
            <button type="button" className="rounded-sm bg-finance px-3 py-1 text-white" disabled={guardando} onClick={() => { setConfirmacionServidor(null); guardar(true); }}>
              Confirmar y guardar
            </button>
            <button type="button" className="rounded-sm border border-border px-3 py-1" onClick={() => setConfirmacionServidor(null)}>
              Volver
            </button>
          </div>
        </div>
      )}
      {error && <p className="text-sm text-status-danger">{error}</p>}

      <div className="flex gap-2">
        <button type="submit" disabled={guardando} className="rounded-sm bg-finance px-5 py-2 text-sm text-white hover:opacity-90 disabled:opacity-40">
          {guardando ? "Guardando…" : edicion ? "Guardar cambios" : "Guardar remito"}
        </button>
        <button type="button" onClick={() => router.back()} className="rounded-sm border border-border px-5 py-2 text-sm text-ink-secondary hover:text-ink-primary">
          Cancelar
        </button>
      </div>
    </form>
  );
}
