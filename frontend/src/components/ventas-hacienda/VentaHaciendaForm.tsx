"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import {
  actualizarVentaHacienda,
  adquirirLockVentaHacienda,
  agregarDocumentoRelacionadoVentaHacienda,
  crearVentaHacienda,
  eliminarVentaHacienda,
  fetchDocumentosRelacionadosVentaHacienda,
  fetchFiltrosVentaHacienda,
  liberarLockVentaHacienda,
  quitarDocumentoRelacionadoVentaHacienda,
  type DocumentoRelacionadoVentaHacienda,
  type VencimientoVentaInput,
  type VentaHaciendaAltaInput,
  type VentaHaciendaDetalle,
} from "@/services/ventasHaciendaApi";
import { ApiError } from "@/services/apiClient";
import { urlDocumentoLocal } from "@/services/comprasApi";
import { formatMoneda } from "@/lib/format";
import { BASE_DOCUMENTOS_VENTAS, esRutaLocalWindows, urlParaAbrirDocumento } from "@/lib/documentoLocal";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { MoneyInput } from "@/components/ui/MoneyInput";
import { filterInputClass } from "@/components/ui/FilterBar";
import { useToast } from "@/components/ui/Toast";
import {
  VentaHaciendaGrid,
  FILA_VACIA_HACIENDA,
  filasARequestLineasHacienda,
  type GridRowHacienda,
} from "@/components/ventas-hacienda/VentaHaciendaGrid";
import { VencimientosVentaHaciendaEditor } from "@/components/ventas-hacienda/VencimientosVentaHaciendaEditor";
import { DocumentosRelacionadosVentaHaciendaPanel } from "@/components/ventas-hacienda/DocumentosRelacionadosVentaHaciendaPanel";

const FILAS_INICIALES = 6;
const inputCompacto = `${filterInputClass} w-full px-1.5 py-1 text-xs`;
const labelCompacto = "flex flex-col gap-0.5 text-xs text-ink-secondary";

function generarUuid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function lineaARow(l: VentaHaciendaDetalle["lineas"][number]): GridRowHacienda {
  return {
    idComprador: l.idComprador,
    compradorNombre: l.comprador ?? null,
    idTipoProducto: String(l.idTipoProducto ?? ""),
    cantidad: l.cantidad ? String(l.cantidad).replace(".", ",") : "",
    unidadMedida: l.unidadMedida ?? "",
    pesoTotal: l.pesoTotal ? String(l.pesoTotal).replace(".", ",") : "",
    precioUnitarioA: l.precioUnitarioA ? String(l.precioUnitarioA).replace(".", ",") : "",
    precioUnitarioB: l.precioUnitarioB ? String(l.precioUnitarioB).replace(".", ",") : "",
  };
}

/**
 * Formulario de alta/edición de Venta de Hacienda (007) — mismo patrón que
 * `CompraForm.tsx` (006): grilla de líneas, vencimientos, documentos
 * relacionados, bloqueo exclusivo de edición. Difiere en que el comprador
 * es por línea (no de cabecera) y en la fórmula de totales propia de Hacienda.
 */
export function VentaHaciendaForm({
  mode,
  idVenta,
  initial,
  consignatarioNombreInicial,
}: {
  mode: "alta" | "edicion";
  idVenta?: number;
  initial?: VentaHaciendaDetalle;
  consignatarioNombreInicial?: string | null;
}) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const { data: filtros } = useQuery({
    queryKey: ["ventas-hacienda-filtros"],
    queryFn: fetchFiltrosVentaHacienda,
    staleTime: Infinity,
  });

  const [idConsignatario, setIdConsignatario] = useState<number | null>(initial?.idConsignatario ?? null);
  const [consignatarioNombre, setConsignatarioNombre] = useState<string | null>(
    consignatarioNombreInicial ?? initial?.consignatario ?? null
  );
  const [idEstablecimiento, setIdEstablecimiento] = useState<string>(
    initial?.idEstablecimiento ? String(initial.idEstablecimiento) : ""
  );
  const [idTipoDocumento, setIdTipoDocumento] = useState<string>(
    initial?.idTipoDocumento ? String(initial.idTipoDocumento) : ""
  );
  const [numeroDocumento, setNumeroDocumento] = useState(initial?.numeroDocumento ?? "");
  const [fecha, setFecha] = useState(initial?.fecha ?? "");
  const [documentoOriginal, setDocumentoOriginal] = useState(initial?.documentoOriginal ?? "");
  const [conceptos, setConceptos] = useState({
    porcComision: initial?.porcComision ?? 0,
    visMunicipal: initial?.visMunicipal ?? 0,
    balanza: initial?.balanza ?? 0,
    gsVsNoGravados: initial?.gsVsNoGravados ?? 0,
    alicuotaIVA: initial?.alicuotaIVA ?? 0,
    retencionGanancias: initial?.retencionGanancias ?? 0,
    retencionIVA: initial?.retencionIVA ?? 0,
    ingresosBrutos: initial?.ingresosBrutos ?? 0,
    leyDeSellos: initial?.leyDeSellos ?? 0,
    flete: initial?.flete ?? 0,
    gastosVarios: initial?.gastosVarios ?? 0,
    complemento: initial?.complemento ?? 0,
  });

  const [rows, setRows] = useState<GridRowHacienda[]>(() => {
    if (initial?.lineas.length) {
      const iniciales = initial.lineas.map(lineaARow);
      const relleno = Math.max(0, FILAS_INICIALES - iniciales.length);
      return [...iniciales, ...Array.from({ length: relleno }, () => ({ ...FILA_VACIA_HACIENDA }))];
    }
    return Array.from({ length: FILAS_INICIALES }, () => ({ ...FILA_VACIA_HACIENDA }));
  });

  const [vencimientos, setVencimientos] = useState<VencimientoVentaInput[]>(
    initial?.vencimientos.map(({ fecha: f, importe }) => ({ fecha: f, importe })) ?? []
  );

  const [isSaving, setIsSaving] = useState(false);
  const [lockToken] = useState(() => generarUuid());
  const [lockError, setLockError] = useState<string | null>(null);

  // Documentos relacionados — mismo patrón que CompraForm.
  const relacionadosKey = ["ventas-hacienda-relacionados", idVenta];
  const { data: relacionadosGuardados } = useQuery({
    queryKey: relacionadosKey,
    queryFn: () => fetchDocumentosRelacionadosVentaHacienda(idVenta!),
    enabled: mode === "edicion" && idVenta != null,
  });
  const [relacionadosPendientes, setRelacionadosPendientes] = useState<DocumentoRelacionadoVentaHacienda[]>([]);
  const relacionadosMostrados = mode === "edicion" ? relacionadosGuardados ?? [] : relacionadosPendientes;

  async function handleVincularRelacionado(doc: DocumentoRelacionadoVentaHacienda) {
    if (mode === "alta" || idVenta == null) {
      setRelacionadosPendientes((prev) => [...prev, doc]);
      return;
    }
    try {
      await agregarDocumentoRelacionadoVentaHacienda(idVenta, doc.idVenta);
      queryClient.invalidateQueries({ queryKey: relacionadosKey });
      showToast("Documento vinculado.", "success");
    } catch {
      showToast("No se pudo vincular el documento.", "danger");
    }
  }

  async function handleDesvincularRelacionado(idVentaRelacionada: number) {
    if (mode === "alta" || idVenta == null) {
      setRelacionadosPendientes((prev) => prev.filter((d) => d.idVenta !== idVentaRelacionada));
      return;
    }
    try {
      await quitarDocumentoRelacionadoVentaHacienda(idVenta, idVentaRelacionada);
      queryClient.invalidateQueries({ queryKey: relacionadosKey });
      showToast("Vínculo quitado.", "neutral");
    } catch {
      showToast("No se pudo quitar el vínculo.", "danger");
    }
  }

  // Totales en vivo — mismas fórmulas de data-model.md (calcular_totales, backend).
  const subTotal = rows.reduce((acc, r) => {
    const cantidad = Number(r.cantidad.replace(",", ".")) || 0;
    const precioA = Number(r.precioUnitarioA.replace(",", ".")) || 0;
    return acc + cantidad * precioA;
  }, 0);
  const subtotalB = rows.reduce((acc, r) => {
    const cantidad = Number(r.cantidad.replace(",", ".")) || 0;
    const precioB = Number(r.precioUnitarioB.replace(",", ".")) || 0;
    return acc + cantidad * precioB;
  }, 0);
  const comision = ((subTotal + subtotalB) * conceptos.porcComision) / 100;
  const iva =
    ((subTotal - conceptos.visMunicipal - conceptos.balanza - comision - conceptos.gsVsNoGravados) *
      conceptos.alicuotaIVA) /
    100;
  const importe =
    subTotal -
    conceptos.visMunicipal -
    conceptos.balanza -
    comision -
    conceptos.gsVsNoGravados +
    iva -
    conceptos.leyDeSellos -
    conceptos.retencionGanancias -
    conceptos.ingresosBrutos -
    conceptos.gastosVarios;
  const importeTotal = importe + subtotalB;

  const lockIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [forzandoLock, setForzandoLock] = useState(false);

  async function handleForzarLock() {
    if (idVenta == null) return;
    setForzandoLock(true);
    try {
      await adquirirLockVentaHacienda(idVenta, lockToken, true);
      setLockError(null);
    } catch {
      showToast("No se pudo forzar la edición. Intentá de nuevo.", "danger");
    } finally {
      setForzandoLock(false);
    }
  }

  useEffect(() => {
    if (mode !== "edicion" || idVenta == null) return;

    let cancelado = false;
    async function adquirir() {
      try {
        await adquirirLockVentaHacienda(idVenta!, lockToken);
        if (!cancelado) setLockError(null);
      } catch {
        if (!cancelado) {
          setLockError(
            "Esta venta está siendo editada en otra sesión. Si sabés que sos vos mismo " +
              "(otra pestaña, o quedó colgada de antes), podés forzar la edición."
          );
        }
      }
    }
    adquirir();
    lockIntervalRef.current = setInterval(adquirir, 2 * 60 * 1000);

    function liberarAlSalir() {
      liberarLockVentaHacienda(idVenta!, lockToken, true).catch(() => {});
    }
    window.addEventListener("pagehide", liberarAlSalir);

    return () => {
      cancelado = true;
      if (lockIntervalRef.current) clearInterval(lockIntervalRef.current);
      window.removeEventListener("pagehide", liberarAlSalir);
      liberarLockVentaHacienda(idVenta!, lockToken).catch(() => {});
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, idVenta]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (idConsignatario == null) {
      showToast("Seleccioná un consignatario.", "danger");
      return;
    }
    if (!idEstablecimiento) {
      showToast("Seleccioná un establecimiento.", "danger");
      return;
    }
    if (!idTipoDocumento) {
      showToast("Seleccioná un tipo de documento.", "danger");
      return;
    }
    const lineas = filasARequestLineasHacienda(rows);
    if (lineas.length === 0) {
      showToast("Agregá al menos una línea con comprador asignado.", "danger");
      return;
    }
    const vencimientosCompletos = vencimientos.filter((v) => v.fecha);

    const input: VentaHaciendaAltaInput = {
      idConsignatario,
      idEstablecimiento: Number(idEstablecimiento),
      idTipoDocumento: Number(idTipoDocumento),
      numeroDocumento,
      fecha,
      ...conceptos,
      documentoOriginal: documentoOriginal || null,
      lineas,
      vencimientos: vencimientosCompletos,
    };

    setIsSaving(true);
    try {
      const resultado =
        mode === "alta" ? await crearVentaHacienda(input) : await actualizarVentaHacienda(idVenta!, input, lockToken);

      if (mode === "alta" && relacionadosPendientes.length > 0) {
        await Promise.all(
          relacionadosPendientes.map((doc) =>
            agregarDocumentoRelacionadoVentaHacienda(resultado.idVenta, doc.idVenta).catch(() => {})
          )
        );
      }

      resultado.warnings.forEach((w) => showToast(w, "neutral"));
      showToast(mode === "alta" ? "Venta de hacienda creada." : "Venta de hacienda actualizada.", "success");
      if (mode === "edicion" && idVenta != null) {
        await liberarLockVentaHacienda(idVenta, lockToken).catch(() => {});
      }
      router.push("/ventas/hacienda");
    } catch (err) {
      const mensaje =
        err instanceof ApiError && err.status === 400 && err.message
          ? err.message
          : "No se pudo guardar la venta. Revisá los datos e intentá de nuevo.";
      showToast(mensaje, "danger");
    } finally {
      setIsSaving(false);
    }
  }

  const [eliminando, setEliminando] = useState(false);

  async function handleEliminar() {
    if (idVenta == null) return;
    if (!window.confirm("¿Eliminar esta venta de hacienda? Esta acción no se puede deshacer.")) return;
    setEliminando(true);
    try {
      await eliminarVentaHacienda(idVenta, lockToken);
      showToast("Venta eliminada.", "success");
      router.push("/ventas/hacienda");
    } catch (err) {
      const mensaje =
        err instanceof ApiError && err.message ? err.message : "No se pudo eliminar la venta. Intentá de nuevo.";
      showToast(mensaje, "danger");
      setEliminando(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-2" suppressHydrationWarning>
      {lockError && (
        <div className="flex shrink-0 items-center justify-between gap-2 rounded-sm border border-status-danger bg-status-danger-bg px-2 py-1 text-xs text-status-danger">
          <span>{lockError}</span>
          <button
            type="button"
            onClick={handleForzarLock}
            disabled={forzandoLock}
            className="whitespace-nowrap rounded-sm border border-status-danger px-2 py-0.5 text-status-danger hover:bg-status-danger hover:text-white disabled:opacity-40"
          >
            {forzandoLock ? "Forzando…" : "Forzar edición"}
          </button>
        </div>
      )}

      <div className="shrink-0 space-y-2">
        <div className="grid grid-cols-[repeat(auto-fit,minmax(10rem,1fr))] items-end gap-2 rounded-md border border-border bg-surface p-2">
          <div className="sm:col-span-2">
            <ContactoSelect
              label="Consignatario"
              tipoContacto={["Comprador", "Consignatario", "Multiple"]}
              value={idConsignatario}
              razonSocial={consignatarioNombre}
              onChange={(id, nombre) => {
                setIdConsignatario(id);
                setConsignatarioNombre(nombre);
              }}
              placeholder="Buscar consignatario…"
            />
          </div>
          <label className={labelCompacto}>
            Establecimiento
            <select
              className={inputCompacto}
              value={idEstablecimiento}
              onChange={(e) => setIdEstablecimiento(e.target.value)}
            >
              <option value="">—</option>
              {filtros?.establecimientos.map((e) => (
                <option key={e.idEstablecimiento} value={e.idEstablecimiento}>
                  {e.establecimiento ?? `#${e.idEstablecimiento}`}
                </option>
              ))}
            </select>
          </label>
          <label className={labelCompacto}>
            Tipo de documento
            <select
              className={inputCompacto}
              value={idTipoDocumento}
              onChange={(e) => setIdTipoDocumento(e.target.value)}
            >
              <option value="">—</option>
              {filtros?.tiposDocumento.map((t) => (
                <option key={t.idTipoDocumento} value={t.idTipoDocumento}>
                  {t.tipoDocumento ?? `#${t.idTipoDocumento}`}
                </option>
              ))}
            </select>
          </label>
          <label className={labelCompacto}>
            Nº documento
            <input
              required
              className={inputCompacto}
              value={numeroDocumento}
              onChange={(e) => setNumeroDocumento(e.target.value.slice(0, 50))}
            />
          </label>
          <label className={labelCompacto}>
            Fecha
            <input
              type="date"
              required
              className={inputCompacto}
              value={fecha}
              onChange={(e) => setFecha(e.target.value)}
            />
          </label>
          <label className={`${labelCompacto} sm:col-span-2`}>
            Documento original (PDF)
            <div className="flex items-center gap-1">
              <input
                className={inputCompacto}
                value={documentoOriginal}
                onChange={(e) => setDocumentoOriginal(e.target.value)}
                placeholder="Link o ruta al PDF escaneado…"
              />
              {documentoOriginal && (
                <a
                  href={urlParaAbrirDocumento(documentoOriginal, BASE_DOCUMENTOS_VENTAS, urlDocumentoLocal)}
                  target="_blank"
                  rel="noreferrer"
                  title={
                    esRutaLocalWindows(documentoOriginal, BASE_DOCUMENTOS_VENTAS)
                      ? "Abre el PDF servido por el backend desde el disco de esta PC."
                      : undefined
                  }
                  className="whitespace-nowrap text-xs text-finance underline"
                >
                  Abrir
                </a>
              )}
            </div>
          </label>
        </div>

        <DocumentosRelacionadosVentaHaciendaPanel
          idConsignatario={idConsignatario}
          relacionados={relacionadosMostrados}
          onVincular={handleVincularRelacionado}
          onDesvincular={handleDesvincularRelacionado}
          excluirIdVenta={idVenta}
        />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <VentaHaciendaGrid rows={rows} onChange={setRows} filtros={filtros} />
      </div>

      <div className="shrink-0 space-y-2">
        <div className="rounded-md border border-border bg-surface p-2 text-xs">
          <VencimientosVentaHaciendaEditor vencimientos={vencimientos} onChange={setVencimientos} />
        </div>

        <div className="flex flex-col gap-2 rounded-md border border-border bg-surface-sunken p-2 xl:flex-row xl:items-start xl:justify-between">
          <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs">
            {(
              [
                ["porcComision", "Comisión %"],
                ["visMunicipal", "Vis. Municipal"],
                ["balanza", "Balanza"],
                ["gsVsNoGravados", "Gs. No Gravados"],
                ["alicuotaIVA", "Alícuota IVA %"],
                ["retencionGanancias", "Ret. Ganancias"],
                ["retencionIVA", "Ret. IVA"],
                ["ingresosBrutos", "Ingresos Brutos"],
                ["leyDeSellos", "Ley de Sellos"],
                ["flete", "Flete"],
                ["gastosVarios", "Gastos Varios"],
                ["complemento", "Complemento"],
              ] as const
            ).map(([key, label]) => (
              <label key={key} className="flex flex-col gap-0.5 text-ink-secondary">
                {label}
                <MoneyInput
                  className={`${inputCompacto} w-24 text-right font-data`}
                  value={conceptos[key]}
                  moneda="Pesos"
                  onChange={(v) => setConceptos({ ...conceptos, [key]: v })}
                />
              </label>
            ))}
          </div>

          <div className="min-w-[14rem] space-y-0.5 text-right text-xs xl:border-l xl:border-border xl:pl-4">
            <p className="font-data text-ink-secondary">
              Subtotal: <span className="text-ink-primary">{formatMoneda(subTotal)}</span>
            </p>
            <p className="font-data text-ink-secondary">
              Subtotal (B): <span className="text-ink-primary">{formatMoneda(subtotalB)}</span>
            </p>
            <p className="font-data text-ink-secondary">
              Comisión: <span className="text-ink-primary">{formatMoneda(comision)}</span>
            </p>
            <p className="font-data text-ink-secondary">
              IVA: <span className="text-ink-primary">{formatMoneda(iva)}</span>
            </p>
            <p className="font-data text-sm font-semibold text-ink-primary">
              Importe total: {formatMoneda(importeTotal)}
            </p>
          </div>
        </div>

        <div className="flex justify-between gap-2">
          {mode === "edicion" ? (
            <button
              type="button"
              onClick={handleEliminar}
              disabled={eliminando || isSaving || lockError != null}
              title={lockError ?? "Eliminar esta venta (ej. cargada por error). No se puede deshacer."}
              className="rounded-sm border border-status-danger px-3 py-1.5 text-xs text-status-danger hover:bg-status-danger-bg disabled:opacity-40"
            >
              {eliminando ? "Eliminando…" : "Eliminar venta"}
            </button>
          ) : (
            <span />
          )}
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => router.push("/ventas/hacienda")}
              className="rounded-sm border border-border px-3 py-1.5 text-xs text-ink-secondary hover:text-ink-primary"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSaving || eliminando || lockError != null}
              className="rounded-sm bg-finance px-3 py-1.5 text-xs text-white hover:opacity-90 disabled:opacity-40"
            >
              {isSaving ? "Guardando…" : "Guardar"}
            </button>
          </div>
        </div>
      </div>
    </form>
  );
}
