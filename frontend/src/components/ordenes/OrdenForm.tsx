"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

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
import {
  CultivoCampaniaLotesSelector,
  lotesBaseDeGrupos,
  type GrupoCultivoCampania,
} from "@/components/ordenes/CultivoCampaniaLotesSelector";
import { formatCantidad } from "@/lib/format";

type Renglon = { idProducto: number | null; producto: string; unidad: string; distribuciones: RenglonInsumoIn["distribuciones"] };

/** Agrega/quita filas de `distribuciones` para que coincidan exactamente con
 * los lotes incluidos en la selección de Cultivo/Campaña de la orden, sin
 * perder la dosis/ha ya cargada en los lotes que siguen incluidos. */
function sincronizarDistribuciones(actuales: RenglonInsumoIn["distribuciones"], base: ReturnType<typeof lotesBaseDeGrupos>): RenglonInsumoIn["distribuciones"] {
  return base.map((b) => {
    const existente = actuales.find((d) => d.idLote === b.idLote && d.idCultivo === b.idCultivo && d.idCampania === b.idCampania);
    return existente ?? { idLote: b.idLote, idCultivo: b.idCultivo, idCampania: b.idCampania, dosisHa: 0, superficie: b.superficie, aplicar: true };
  });
}

/** Reconstruye los grupos Cultivo/Campaña de una orden existente a partir de
 * sus distribuciones ya guardadas, agregando también los lotes que la
 * Planificación Agrícola sugiere hoy para ese mismo Cultivo/Campaña (por si el
 * plan cambió desde que se cargó la orden) — nada de lo ya guardado desaparece. */
function gruposDesdeOrden(orden: OrdenDetalle, planAgricola: { idLote: number; numeroLote: string | null; superficie: number | null; idCultivo: number; cultivo: string | null; idCampania: number; campania: string | null }[]): GrupoCultivoCampania[] {
  const grupos = new Map<string, GrupoCultivoCampania>();
  for (const insumo of orden.insumos) {
    for (const d of insumo.distribuciones) {
      const clave = `${d.idCultivo}-${d.idCampania}`;
      if (!grupos.has(clave)) {
        grupos.set(clave, { idCultivo: d.idCultivo, idCampania: d.idCampania, cultivo: d.cultivo ?? "", campania: d.campania ?? "", lotes: [] });
      }
      const g = grupos.get(clave)!;
      if (!g.lotes.some((l) => l.idLote === d.idLote)) {
        const enPlan = planAgricola.some((p) => p.idLote === d.idLote && p.idCultivo === d.idCultivo && p.idCampania === d.idCampania);
        g.lotes.push({ idLote: d.idLote, numeroLote: d.lote ?? String(d.idLote), superficie: d.superficie, incluido: true, fueraDelPlan: !enPlan });
      }
    }
  }
  for (const g of grupos.values()) {
    for (const p of planAgricola) {
      if (p.idCultivo === g.idCultivo && p.idCampania === g.idCampania && !g.lotes.some((l) => l.idLote === p.idLote)) {
        g.lotes.push({ idLote: p.idLote, numeroLote: p.numeroLote ?? String(p.idLote), superficie: p.superficie ?? 0, incluido: false });
      }
    }
  }
  return [...grupos.values()];
}

/**
 * Alta/edición de una Orden de Trabajo (Historia 1): Cultivo/Campaña y sus
 * lotes primero (sugeridos por la Planificación Agrícola), después tipo de
 * labor, contratista e insumos con su dosis/ha por lote. Al guardar se
 * descuenta stock por FIFO y se emite el Formulario de Retiro (FR-008).
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
  const [grupos, setGrupos] = useState<GrupoCultivoCampania[]>([]);
  const [gruposInicializados, setGruposInicializados] = useState(false);
  const [renglones, setRenglones] = useState<Renglon[]>(
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

  useEffect(() => {
    if (!catalogos || gruposInicializados) return;
    if (orden) setGrupos(gruposDesdeOrden(orden, catalogos.planAgricola));
    setGruposInicializados(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [catalogos, gruposInicializados]);

  const lotesBase = lotesBaseDeGrupos(grupos);

  // Cada vez que cambia el set de lotes incluidos, cada renglón de insumo
  // sincroniza sus filas de dosis/ha sin perder lo ya cargado (ver arriba).
  useEffect(() => {
    if (!gruposInicializados) return;
    setRenglones((actuales) => {
      const sincronizados = actuales.map((r) => ({ ...r, distribuciones: sincronizarDistribuciones(r.distribuciones, lotesBase) }));
      const cambio = sincronizados.some((r, i) => r.distribuciones !== actuales[i].distribuciones && JSON.stringify(r.distribuciones) !== JSON.stringify(actuales[i].distribuciones));
      return cambio ? sincronizados : actuales;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(lotesBase), gruposInicializados]);

  if (!catalogos) return <p className="text-ink-secondary">Cargando catálogos…</p>;

  const agregarRenglon = () =>
    setRenglones([...renglones, { idProducto: null, producto: "", unidad: "LTS", distribuciones: sincronizarDistribuciones([], lotesBase) }]);

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
    if (!sinCultivo && lotesBase.length === 0) {
      setError("Elegí al menos un Cultivo/Campaña y sus lotes.");
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

  // Totales del punto 6: superficie por Cultivo/Campaña y total de cada
  // insumo, también desglosado por Cultivo/Campaña.
  const superficiePorGrupo = grupos.map((g) => ({
    clave: `${g.idCultivo}-${g.idCampania}`,
    etiqueta: `${g.cultivo} — ${g.campania}`,
    superficie: g.lotes.filter((l) => l.incluido).reduce((acc, l) => acc + l.superficie, 0),
  }));
  const superficieTotal = superficiePorGrupo.reduce((acc, g) => acc + g.superficie, 0);

  const totalesInsumos = renglones
    .filter((r) => r.idProducto)
    .map((r) => {
      const porGrupo = superficiePorGrupo.map((g) => {
        const [gc, gca] = g.clave.split("-").map(Number);
        const total = r.distribuciones.filter((d) => d.aplicar && d.idCultivo === gc && d.idCampania === gca).reduce((acc, d) => acc + d.dosisHa * d.superficie, 0);
        return { etiqueta: g.etiqueta, total };
      });
      const total = porGrupo.reduce((acc, g) => acc + g.total, 0);
      return { producto: r.producto, unidad: r.unidad, total, porGrupo };
    });

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

      {!sinCultivo && (
        <div>
          <h2 className="mb-2 text-lg font-medium">Cultivo / Campaña y lotes</h2>
          <CultivoCampaniaLotesSelector
            cultivos={catalogos.cultivos}
            campanias={catalogos.campanias}
            planAgricola={catalogos.planAgricola}
            grupos={grupos}
            onChange={setGrupos}
          />
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
                grupos={grupos}
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

      {(superficiePorGrupo.length > 0 || totalesInsumos.length > 0) && (
        <div className="rounded border border-border bg-surface-sunken p-3">
          <h2 className="mb-2 text-lg font-medium">Resumen</h2>
          {superficiePorGrupo.length > 0 && (
            <div className="mb-3">
              <p className="text-sm font-medium">Superficie afectada: {formatCantidad(superficieTotal)} ha</p>
              <ul className="ml-4 list-disc text-sm text-ink-secondary">
                {superficiePorGrupo.map((g) => (
                  <li key={g.clave}>
                    {g.etiqueta}: {formatCantidad(g.superficie)} ha
                  </li>
                ))}
              </ul>
            </div>
          )}
          {totalesInsumos.length > 0 && (
            <div>
              <p className="text-sm font-medium">Insumos</p>
              <ul className="ml-4 list-disc text-sm text-ink-secondary">
                {totalesInsumos.map((t, i) => (
                  <li key={i}>
                    {t.producto}: {formatCantidad(t.total)} {t.unidad}
                    {t.porGrupo.length > 1 && (
                      <ul className="ml-4 list-[circle]">
                        {t.porGrupo.map((g) => (
                          <li key={g.etiqueta}>
                            {g.etiqueta}: {formatCantidad(g.total)} {t.unidad}
                          </li>
                        ))}
                      </ul>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

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
