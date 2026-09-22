"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ProductoSelect } from "@/components/remitos/ProductoSelect";
import { ApiError } from "@/services/apiClient";
import { fetchOpcionesBajas } from "@/services/remitosApi";
import {
  crearOrden,
  editarOrden,
  fetchCatalogosOrdenes,
  type OrdenDetalle,
  type OrdenIn,
  type RenglonInsumoIn,
} from "@/services/ordenesApi";
import { DistribucionLotesPanel } from "@/components/ordenes/DistribucionLotesPanel";

/**
 * Alta/edición de una Orden de Trabajo (Historia 1): cabecera, y por cada
 * insumo, el reparto por lote/dosis. Al guardar se descuenta stock por FIFO y
 * se emite el Formulario de Retiro con su propio número (FR-008).
 */
export function OrdenForm({ orden }: { orden?: OrdenDetalle }) {
  const router = useRouter();
  const { data: catalogos } = useQuery({ queryKey: ["ordenes", "catalogos"], queryFn: fetchCatalogosOrdenes });
  const { data: opcionesBajas } = useQuery({ queryKey: ["opciones-bajas"], queryFn: fetchOpcionesBajas });

  const [fecha, setFecha] = useState(orden?.fechaPedido ?? new Date().toISOString().slice(0, 10));
  const [idTipoLabor, setIdTipoLabor] = useState<number | null>(orden?.idTipoLabor ?? null);
  const [idContratistaContacto, setIdContratistaContacto] = useState<number | null>(orden?.idContratistaContacto ?? null);
  const [observaciones, setObservaciones] = useState(orden?.observaciones ?? "");
  const [sinCultivo, setSinCultivo] = useState(orden?.idRubro != null);
  const [idRubro, setIdRubro] = useState<number | null>(orden?.idRubro ?? null);
  const [idCentroCostos, setIdCentroCostos] = useState<number | null>(orden?.idCentroCostos ?? null);
  const [renglones, setRenglones] = useState<
    { idProducto: number | null; producto: string; unidad: string; distribuciones: RenglonInsumoIn["distribuciones"] }[]
  >(
    orden?.insumos.map((i) => ({
      idProducto: i.idProducto,
      producto: i.producto ?? "",
      unidad: i.unidad,
      distribuciones: i.distribuciones.map((d) => ({
        idLote: d.idLote,
        idCultivo: d.idCultivo,
        idCampania: d.idCampania,
        dosisHa: d.dosisHa,
        superficie: d.superficie,
        aplicar: d.aplicar,
      })),
    })) ?? []
  );
  const [error, setError] = useState<string | null>(null);
  const [advertencias, setAdvertencias] = useState<string[] | null>(null);
  const [guardando, setGuardando] = useState(false);

  if (!catalogos) return <p className="text-ink-secondary">Cargando catálogos…</p>;

  const agregarRenglon = () =>
    setRenglones([...renglones, { idProducto: null, producto: "", unidad: "LTS", distribuciones: [] }]);

  const quitarRenglon = (i: number) => setRenglones(renglones.filter((_, idx) => idx !== i));

  const construirDatos = (confirmar: boolean): OrdenIn => ({
    fecha,
    idTipoLabor: idTipoLabor ?? 0,
    idContratistaContacto,
    renglones: renglones.map((r) => ({ idProducto: r.idProducto ?? 0, unidad: r.unidad, distribuciones: r.distribuciones })),
    idRubro: sinCultivo ? idRubro : null,
    idCentroCostos: sinCultivo ? idCentroCostos : null,
    observaciones: observaciones || null,
    confirmar,
  });

  const guardar = async (confirmar = false) => {
    setError(null);
    if (!idTipoLabor) {
      setError("Elegí el tipo de labor.");
      return;
    }
    if (renglones.length === 0 || renglones.some((r) => !r.idProducto || r.distribuciones.length === 0)) {
      setError("Cada renglón necesita un producto y al menos un lote.");
      return;
    }
    setGuardando(true);
    try {
      const datos = construirDatos(confirmar);
      if (orden) {
        await editarOrden(orden.idOrden, datos);
        router.push(`/produccion/ordenes/${orden.idOrden}`);
      } else {
        const res = await crearOrden(datos);
        router.push(`/produccion/ordenes/${res.idOrden}`);
      }
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setAdvertencias(e.message.split(" "));
      } else {
        setError(e instanceof Error ? e.message : "No se pudo guardar la orden.");
      }
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <label className="block text-sm">
          Fecha
          <input type="date" className="mt-1 w-full rounded border border-border px-2 py-1.5" value={fecha} onChange={(e) => setFecha(e.target.value)} />
        </label>
        <label className="block text-sm">
          Tipo de labor
          <select
            className="mt-1 w-full rounded border border-border px-2 py-1.5"
            value={idTipoLabor ?? ""}
            onChange={(e) => setIdTipoLabor(Number(e.target.value) || null)}
          >
            <option value="">Elegí…</option>
            {catalogos.tiposLabor.map((t) => (
              <option key={t.idTipoLabor} value={t.idTipoLabor}>
                {t.nombre}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          Contratista (opcional)
          <select
            className="mt-1 w-full rounded border border-border px-2 py-1.5"
            value={idContratistaContacto ?? ""}
            onChange={(e) => setIdContratistaContacto(Number(e.target.value) || null)}
          >
            <option value="">Maquinaria propia / sin definir</option>
            {catalogos.contratistas.map((c) => (
              <option key={c.idContratistaContacto} value={c.idContratistaContacto}>
                {c.nombre}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={sinCultivo} onChange={(e) => setSinCultivo(e.target.checked)} />
        Orden de mantenimiento general (sin cultivo específico) — se imputa a Rubro y Centro de Costos, no a Cultivo/Campaña
      </label>
      {sinCultivo && opcionesBajas && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <label className="block text-sm">
            Rubro
            <select className="mt-1 w-full rounded border border-border px-2 py-1.5" value={idRubro ?? ""} onChange={(e) => setIdRubro(Number(e.target.value) || null)}>
              <option value="">Elegí…</option>
              {opcionesBajas.rubros.map((r) => (
                <option key={r.idRubro} value={r.idRubro}>
                  {r.rubro}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            Centro de costos
            <select className="mt-1 w-full rounded border border-border px-2 py-1.5" value={idCentroCostos ?? ""} onChange={(e) => setIdCentroCostos(Number(e.target.value) || null)}>
              <option value="">Elegí…</option>
              {opcionesBajas.centros.map((c) => (
                <option key={c.idCentro} value={c.idCentro}>
                  {c.centro}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}

      <div>
        <h2 className="mb-2 text-lg font-medium">Insumos</h2>
        <div className="space-y-4">
          {renglones.map((r, i) => (
            <div key={i} className="rounded border border-border p-3">
              <div className="mb-2 flex items-center gap-3">
                <ProductoSelect
                  value={r.idProducto ? { idProducto: r.idProducto, producto: r.producto } : null}
                  onChange={(p) => {
                    const copia = [...renglones];
                    copia[i] = { ...copia[i], idProducto: p.idProducto, producto: p.producto, unidad: p.unidadBase ?? copia[i].unidad };
                    setRenglones(copia);
                  }}
                  className="flex-1"
                />
                <button type="button" onClick={() => quitarRenglon(i)} className="text-status-danger hover:underline">
                  Quitar renglón
                </button>
              </div>
              <DistribucionLotesPanel
                lotes={catalogos.lotes}
                cultivos={catalogos.cultivos}
                campanias={catalogos.campanias}
                distribuciones={r.distribuciones}
                onChange={(d) => {
                  const copia = [...renglones];
                  copia[i] = { ...copia[i], distribuciones: d };
                  setRenglones(copia);
                }}
              />
            </div>
          ))}
        </div>
        <button type="button" onClick={agregarRenglon} className="mt-3 rounded border border-border px-3 py-1.5 text-sm hover:bg-surface-sunken">
          + Agregar insumo
        </button>
      </div>

      <label className="block text-sm">
        Observaciones
        <textarea className="mt-1 w-full rounded border border-border px-2 py-1.5" value={observaciones} onChange={(e) => setObservaciones(e.target.value)} />
      </label>

      {error && <p className="text-status-danger">{error}</p>}

      {advertencias && (
        <div className="rounded border border-status-warning bg-status-warning-bg p-3">
          <p className="font-medium text-status-warning">El consumo dejaría stock negativo:</p>
          <ul className="list-disc pl-5 text-sm">
            {advertencias.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
          <div className="mt-2 flex gap-2">
            <button type="button" onClick={() => guardar(true)} className="rounded bg-finance px-3 py-1.5 text-sm text-white">
              Confirmar igual
            </button>
            <button type="button" onClick={() => setAdvertencias(null)} className="rounded border border-border px-3 py-1.5 text-sm">
              Cancelar
            </button>
          </div>
        </div>
      )}

      <button
        type="button"
        onClick={() => guardar(false)}
        disabled={guardando}
        className="rounded bg-finance px-4 py-2 text-white disabled:opacity-50"
      >
        {guardando ? "Guardando…" : orden ? "Guardar cambios" : "Planificar orden"}
      </button>
    </div>
  );
}
