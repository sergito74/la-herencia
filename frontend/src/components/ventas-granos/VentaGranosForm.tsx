"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import {
  actualizarVentaGranos,
  adquirirLockVentaGranos,
  crearVentaGranos,
  eliminarVentaGranos,
  fetchFiltrosVentasGranos,
  liberarLockVentaGranos,
  type AjusteInput,
  type DeduccionInput,
  type VentaGranosAltaInput,
  type VentaGranosDetalle,
} from "@/services/ventasGranosApi";
import { ApiError } from "@/services/apiClient";
import { urlDocumentoLocal } from "@/services/comprasApi";
import { formatMoneda } from "@/lib/format";
import { BASE_DOCUMENTOS_VENTAS, esRutaLocalWindows, urlParaAbrirDocumento } from "@/lib/documentoLocal";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { MoneyInput } from "@/components/ui/MoneyInput";
import { filterInputClass } from "@/components/ui/FilterBar";
import { useToast } from "@/components/ui/Toast";
import { AjustesEditor } from "@/components/ventas-granos/AjustesEditor";
import { DeduccionesEditor } from "@/components/ventas-granos/DeduccionesEditor";
import { NumberInput } from "@/components/ui/NumberInput";

const inputCompacto = `${filterInputClass} w-full px-1.5 py-1 text-xs`;
const labelCompacto = "flex flex-col gap-0.5 text-xs text-ink-secondary";

function generarUuid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

/**
 * Formulario de alta/edición de Venta de Granos (007) — estructuralmente
 * distinto de Compras/Hacienda: una sola fila de cabecera (sin líneas de
 * producto), con dos listas editables chicas (Ajustes/Deducciones, no
 * grillas tipo planilla). `campania` es texto libre, no un combo cerrado
 * (research.md §3: valores históricos reales inconsistentes).
 */
export function VentaGranosForm({
  mode,
  idVenta,
  initial,
  consignatarioNombreInicial,
}: {
  mode: "alta" | "edicion";
  idVenta?: number;
  initial?: VentaGranosDetalle;
  consignatarioNombreInicial?: string | null;
}) {
  const router = useRouter();
  const { showToast } = useToast();

  const { data: filtros } = useQuery({
    queryKey: ["ventas-granos-filtros"],
    queryFn: fetchFiltrosVentasGranos,
    staleTime: Infinity,
  });

  const [idConsignatario, setIdConsignatario] = useState<number | null>(initial?.idConsignatario ?? null);
  const [consignatarioNombre, setConsignatarioNombre] = useState<string | null>(
    consignatarioNombreInicial ?? null
  );
  const [idTipoDocumento, setIdTipoDocumento] = useState<string>(
    initial?.idTipoDocumento ? String(initial.idTipoDocumento) : ""
  );
  const [idProducto, setIdProducto] = useState<string>(initial?.idProducto ? String(initial.idProducto) : "");
  const [numeroDocumento, setNumeroDocumento] = useState(initial?.numeroDocumento ?? "");
  const [fecha, setFecha] = useState(initial?.fecha ?? "");
  const [precioUnitario, setPrecioUnitario] = useState(initial?.precioUnitario ?? 0);
  const [tipoCambio, setTipoCambio] = useState<number | null>(initial?.tipoCambio ?? null);
  const [gradoOperacion, setGradoOperacion] = useState(initial?.gradoOperacion ?? "");
  const [tipoDeGrano, setTipoDeGrano] = useState(initial?.tipoDeGrano ?? "");
  const [campania, setCampania] = useState(initial?.campania ?? "");
  const [flete, setFlete] = useState(initial?.flete ?? 0);
  const [nroDeposito, setNroDeposito] = useState(initial?.nroDeposito ?? "");
  const [gradoMercaderia, setGradoMercaderia] = useState(initial?.gradoMercaderia ?? "");
  const [factor, setFactor] = useState(initial?.factor ?? 100);
  const [contProteico, setContProteico] = useState<number | null>(initial?.contProteico ?? null);
  const [cantidadEntregada, setCantidadEntregada] = useState(initial?.cantidadEntregada ?? 0);
  const [cantidadVendida, setCantidadVendida] = useState(initial?.cantidadVendida ?? 0);
  const [alicuotaIVA, setAlicuotaIVA] = useState(initial?.alicuotaIVA ?? 0);
  const [retencionIVA, setRetencionIVA] = useState(initial?.retencionIVA ?? 0);
  const [retIG, setRetIG] = useState(initial?.retIG ?? 0);
  const [percepciones, setPercepciones] = useState(initial?.percepciones ?? 0);
  const [otraRetenciones, setOtraRetenciones] = useState(initial?.otraRetenciones ?? 0);
  const [sellado, setSellado] = useState(initial?.sellado ?? 0);
  const [derechoRegistro, setDerechoRegistro] = useState(initial?.derechoRegistro ?? 0);
  const [honorariosCamara, setHonorariosCamara] = useState(initial?.honorariosCamara ?? 0);
  const [aCuentaCalidad, setACuentaCalidad] = useState(initial?.aCuentaCalidad ?? 0);
  const [iibb, setIibb] = useState(initial?.iibb ?? 0);
  const [documentoOriginal, setDocumentoOriginal] = useState(initial?.documentoOriginal ?? "");

  const [ajustes, setAjustes] = useState<AjusteInput[]>(
    initial?.ajustes.map((a) => ({
      concepto: a.concepto ?? "",
      importe: a.importe ?? 0,
      alicuotaIVA: a.alicuotaIVA ?? 0,
    })) ?? []
  );
  const [deducciones, setDeducciones] = useState<DeduccionInput[]>(
    initial?.deducciones.map((d) => ({
      idConcepto: d.idConcepto ?? 0,
      detalle: d.detalle ?? "",
      porc: d.porc ?? 0,
      baseCalculo: d.baseCalculo ?? 0,
      alicuota: d.alicuota ?? 0,
    })) ?? []
  );

  const [isSaving, setIsSaving] = useState(false);
  const [lockToken] = useState(() => generarUuid());
  const [lockError, setLockError] = useState<string | null>(null);

  // Totales en vivo — mismas fórmulas de data-model.md (calcular_totales, backend).
  const precioKg = (precioUnitario * factor / 100 - flete) / 1000;
  const sumaAjustes = ajustes.reduce((acc, a) => acc + (a.importe || 0), 0);
  const subTotal = cantidadVendida * precioKg + sumaAjustes;
  const iva = (subTotal * alicuotaIVA) / 100;
  const totalOperacion = subTotal + iva;
  const totalRetenciones = retIG + retencionIVA;
  const totalDeducciones = deducciones.reduce((acc, d) => {
    const base = d.baseCalculo * (d.porc / 100);
    return acc + base + (base * (d.alicuota ?? 0)) / 100;
  }, 0);
  const importeNetoAPercibir = totalOperacion - (totalRetenciones + percepciones + otraRetenciones + totalDeducciones);

  const lockIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [forzandoLock, setForzandoLock] = useState(false);

  async function handleForzarLock() {
    if (idVenta == null) return;
    setForzandoLock(true);
    try {
      await adquirirLockVentaGranos(idVenta, lockToken, true);
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
        await adquirirLockVentaGranos(idVenta!, lockToken);
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
      liberarLockVentaGranos(idVenta!, lockToken, true).catch(() => {});
    }
    window.addEventListener("pagehide", liberarAlSalir);

    return () => {
      cancelado = true;
      if (lockIntervalRef.current) clearInterval(lockIntervalRef.current);
      window.removeEventListener("pagehide", liberarAlSalir);
      liberarLockVentaGranos(idVenta!, lockToken).catch(() => {});
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, idVenta]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (idConsignatario == null) {
      showToast("Seleccioná un consignatario.", "danger");
      return;
    }
    if (!idTipoDocumento) {
      showToast("Seleccioná un tipo de documento.", "danger");
      return;
    }
    if (!idProducto) {
      showToast("Seleccioná un grano.", "danger");
      return;
    }

    const input: VentaGranosAltaInput = {
      idConsignatario,
      idTipoDocumento: Number(idTipoDocumento),
      idProducto: Number(idProducto),
      numeroDocumento,
      fecha,
      precioUnitario,
      tipoCambio,
      gradoOperacion: gradoOperacion || null,
      tipoDeGrano: tipoDeGrano || null,
      campania: campania || null,
      flete,
      nroDeposito: nroDeposito || null,
      gradoMercaderia: gradoMercaderia || null,
      factor,
      contProteico,
      cantidadEntregada,
      cantidadVendida,
      alicuotaIVA,
      retencionIVA,
      retIG,
      percepciones,
      otraRetenciones,
      sellado,
      derechoRegistro,
      honorariosCamara,
      aCuentaCalidad,
      iibb,
      documentoOriginal: documentoOriginal || null,
      ajustes: ajustes.filter((a) => a.concepto.trim()),
      deducciones,
    };

    setIsSaving(true);
    try {
      const resultado =
        mode === "alta" ? await crearVentaGranos(input) : await actualizarVentaGranos(idVenta!, input, lockToken);

      resultado.warnings.forEach((w) => showToast(w, "neutral"));
      showToast(mode === "alta" ? "Venta de granos creada." : "Venta de granos actualizada.", "success");
      if (mode === "edicion" && idVenta != null) {
        await liberarLockVentaGranos(idVenta, lockToken).catch(() => {});
      }
      router.push("/ventas/granos");
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
    if (!window.confirm("¿Eliminar esta venta de granos? Esta acción no se puede deshacer.")) return;
    setEliminando(true);
    try {
      await eliminarVentaGranos(idVenta, lockToken);
      showToast("Venta eliminada.", "success");
      router.push("/ventas/granos");
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
          Tipo de documento
          <select className={inputCompacto} value={idTipoDocumento} onChange={(e) => setIdTipoDocumento(e.target.value)}>
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
            onChange={(e) => setNumeroDocumento(e.target.value.slice(0, 255))}
          />
        </label>
        <label className={labelCompacto}>
          Fecha
          <input type="date" required className={inputCompacto} value={fecha} onChange={(e) => setFecha(e.target.value)} />
        </label>
        <label className={labelCompacto}>
          Grano
          <select className={inputCompacto} value={idProducto} onChange={(e) => setIdProducto(e.target.value)}>
            <option value="">—</option>
            {filtros?.granos.map((g) => (
              <option key={g.idGrano} value={g.idGrano}>
                {g.grano ?? `#${g.idGrano}`}
              </option>
            ))}
          </select>
        </label>
        <label className={labelCompacto}>
          Tipo de grano (texto)
          <input className={inputCompacto} value={tipoDeGrano} onChange={(e) => setTipoDeGrano(e.target.value)} />
        </label>
        <label className={labelCompacto}>
          {/* Texto libre, no combo cerrado (research.md §3) — históricos reales
              inconsistentes ('2011' vs '2010/2011'). */}
          Campaña
          <input
            className={inputCompacto}
            maxLength={10}
            value={campania}
            onChange={(e) => setCampania(e.target.value)}
            placeholder="Ej. 2010/2011"
          />
        </label>
        <label className={labelCompacto}>
          Precio unitario
          <MoneyInput className={`${inputCompacto} text-right font-data`} value={precioUnitario} moneda="Pesos" onChange={setPrecioUnitario} />
        </label>
        <label className={labelCompacto}>
          Tipo de cambio
          <NumberInput className={inputCompacto} value={tipoCambio} onChange={setTipoCambio} minDecimales={2} maxDecimales={4} />
        </label>
        <label className={labelCompacto}>
          Cantidad entregada
          <NumberInput
            required
            className={`${inputCompacto} text-right font-data`}
            value={cantidadEntregada}
            onChange={(v) => setCantidadEntregada(v ?? 0)}
          />
        </label>
        <label className={labelCompacto}>
          Cantidad vendida
          <NumberInput
            required
            className={`${inputCompacto} text-right font-data`}
            value={cantidadVendida}
            onChange={(v) => setCantidadVendida(v ?? 0)}
          />
        </label>
        <label className={labelCompacto}>
          Factor
          <NumberInput className={`${inputCompacto} text-right font-data`} value={factor} onChange={(v) => setFactor(v ?? 0)} />
        </label>
        <label className={labelCompacto}>
          Grado operación
          <input className={inputCompacto} maxLength={5} value={gradoOperacion} onChange={(e) => setGradoOperacion(e.target.value)} />
        </label>
        <label className={labelCompacto}>
          Grado mercadería
          <input className={inputCompacto} maxLength={5} value={gradoMercaderia} onChange={(e) => setGradoMercaderia(e.target.value)} />
        </label>
        <label className={labelCompacto}>
          Cont. proteico
          <NumberInput className={`${inputCompacto} text-right font-data`} value={contProteico} onChange={setContProteico} />
        </label>
        <label className={labelCompacto}>
          Nº depósito
          <input className={inputCompacto} value={nroDeposito} onChange={(e) => setNroDeposito(e.target.value)} />
        </label>
        <label className="sm:col-span-2">
          <span className="text-xs text-ink-secondary">Documento original (PDF)</span>
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

      <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
        <AjustesEditor ajustes={ajustes} onChange={setAjustes} />
        <DeduccionesEditor deducciones={deducciones} onChange={setDeducciones} filtros={filtros} />
      </div>

      <div className="flex flex-col gap-2 rounded-md border border-border bg-surface-sunken p-2 xl:flex-row xl:items-start xl:justify-between">
        <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs">
          {(
            [
              ["flete", "Flete", flete, setFlete],
              ["alicuotaIVA", "Alícuota IVA %", alicuotaIVA, setAlicuotaIVA],
              ["retencionIVA", "Ret. IVA", retencionIVA, setRetencionIVA],
              ["retIG", "Ret. IG", retIG, setRetIG],
              ["percepciones", "Percepciones", percepciones, setPercepciones],
              ["otraRetenciones", "Otras retenciones", otraRetenciones, setOtraRetenciones],
              ["sellado", "Sellado", sellado, setSellado],
              ["derechoRegistro", "Derecho de registro", derechoRegistro, setDerechoRegistro],
              ["honorariosCamara", "Honorarios cámara", honorariosCamara, setHonorariosCamara],
              ["aCuentaCalidad", "A cuenta de calidad", aCuentaCalidad, setACuentaCalidad],
              ["iibb", "IIBB", iibb, setIibb],
            ] as [string, string, number, (v: number) => void][]
          ).map(([key, label, value, setter]) => (
            <label key={key} className="flex flex-col gap-0.5 text-ink-secondary">
              {label}
              <MoneyInput className={`${inputCompacto} w-24 text-right font-data`} value={value} moneda="Pesos" onChange={setter} />
            </label>
          ))}
        </div>

        <div className="min-w-[14rem] space-y-0.5 text-right text-xs xl:border-l xl:border-border xl:pl-4">
          <p className="font-data text-ink-secondary">
            Precio/kg: <span className="text-ink-primary">{formatMoneda(precioKg)}</span>
          </p>
          <p className="font-data text-ink-secondary">
            Subtotal: <span className="text-ink-primary">{formatMoneda(subTotal)}</span>
          </p>
          <p className="font-data text-ink-secondary">
            IVA: <span className="text-ink-primary">{formatMoneda(iva)}</span>
          </p>
          <p className="font-data text-ink-secondary">
            Total deducciones: <span className="text-ink-primary">{formatMoneda(totalDeducciones)}</span>
          </p>
          <p className="font-data text-sm font-semibold text-ink-primary">
            Neto a percibir: {formatMoneda(importeNetoAPercibir)}
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
            onClick={() => router.push("/ventas/granos")}
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
    </form>
  );
}
