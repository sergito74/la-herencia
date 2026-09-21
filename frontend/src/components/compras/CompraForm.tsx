"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import {
  actualizarCompra,
  adquirirLock,
  agregarDocumentoRelacionado,
  crearCompra,
  eliminarCompra,
  fetchDocumentosRelacionados,
  fetchFiltrosCompras,
  liberarLock,
  quitarDocumentoRelacionado,
  TIPOS_CONTACTO_COMPRA,
  type CompraAltaInput,
  type CompraDetalleCompleto,
  type DocumentoRelacionado,
  type MonedaCompra,
  type TipoComprobante,
  type TipoDocumentoCompra,
  type VencimientoInput,
  urlDocumentoLocal,
} from "@/services/comprasApi";
import { ApiError } from "@/services/apiClient";
import { formatMoneda, numeroAEdicionLocal } from "@/lib/format";
import {
  BASE_DOCUMENTOS_COMPRAS,
  esRutaLocalWindows,
  limpiarRutaCopiada,
  urlParaAbrirDocumento,
} from "@/lib/documentoLocal";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { MoneyInput } from "@/components/ui/MoneyInput";
import { filterInputClass } from "@/components/ui/FilterBar";
import { useToast } from "@/components/ui/Toast";
import { ComprasGrid, FILA_VACIA, calcularLinea, filasARequestLineas, type GridRow } from "@/components/compras/ComprasGrid";
import { DocumentosRelacionadosPanel } from "@/components/compras/DocumentosRelacionadosPanel";
import { VencimientosEditor } from "@/components/compras/VencimientosEditor";

const TIPOS_COMPROBANTE: TipoComprobante[] = ["A", "B", "C", "M", "X"];
const TIPOS_DOCUMENTO: TipoDocumentoCompra[] = [
  "Factura",
  "Nota de Crédito",
  "Nota de Débito",
  "C. Deposito Cereales",
];

const FILAS_INICIALES = 10;
const inputCompacto = `${filterInputClass} w-full px-1.5 py-1 text-xs`;
const labelCompacto = "flex flex-col gap-0.5 text-xs text-ink-secondary";

function generarUuid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function lineaARow(l: CompraDetalleCompleto["lineas"][number]): GridRow {
  return {
    cantidad: l.cantidad ? numeroAEdicionLocal(l.cantidad) : "",
    unidad: l.unidad ?? "",
    productoServicio: l.productoServicio,
    // Rubro/Centro de Costos/Destino llegan como id — se resuelven a texto
    // recién cuando los catálogos (`filtros`) terminan de cargar, ver efecto abajo.
    rubro: "",
    centroCosto: "",
    destino: "",
    campania: l.campaña ?? "",
    precioUnitario: l.precioUnitario ? numeroAEdicionLocal(l.precioUnitario) : "",
    iva: l.iva ? numeroAEdicionLocal(l.iva) : "",
  };
}

/**
 * Formulario de alta/edición de Compras (006-carga-compras): grilla tipo
 * planilla de cálculo con encabezado y pie fijos (solo el cuerpo scrollea),
 * catálogos cerrados en Rubro/Centro de Costos/Destino/Campaña, y vínculo
 * manual de documentos relacionados (Notas de Crédito/Débito que
 * complementan una Factura).
 */
export function CompraForm({
  mode,
  idCompra,
  initial,
  proveedorNombreInicial,
  prefill,
}: {
  mode: "alta" | "edicion";
  idCompra?: number;
  initial?: CompraDetalleCompleto;
  proveedorNombreInicial?: string | null;
  /** Datos para arrancar un alta con algo cargado (ej. desde la conciliación de tarjetas). */
  prefill?: {
    idContacto?: number | null;
    proveedorNombre?: string | null;
    fecha?: string;
    numeroDocumento?: string;
    detalle?: string;
    importe?: number;
  };
}) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const { data: filtros, refetch: refetchFiltros } = useQuery({
    queryKey: ["compras-filtros"],
    queryFn: fetchFiltrosCompras,
    staleTime: Infinity,
  });

  const [idContacto, setIdContacto] = useState<number | null>(initial?.idContacto ?? prefill?.idContacto ?? null);
  const [razonSocialProveedor, setRazonSocialProveedor] = useState<string | null>(
    proveedorNombreInicial ?? prefill?.proveedorNombre ?? null
  );
  const [fecha, setFecha] = useState(initial?.fecha ?? prefill?.fecha ?? "");
  const [tipo, setTipo] = useState<TipoComprobante>(initial?.tipo ?? "A");
  const [tipoDocumento, setTipoDocumento] = useState<TipoDocumentoCompra>(
    initial?.tipoDocumento ?? "Factura"
  );
  const [numeroDocumento, setNumeroDocumento] = useState(initial?.numeroDocumento ?? prefill?.numeroDocumento ?? "");
  const [moneda, setMonedaState] = useState<MonedaCompra>(initial?.moneda ?? "Pesos");
  const [tipoDeCambio, setTipoDeCambio] = useState<number | null>(
    initial?.moneda === "Dolares" ? initial?.tipoDeCambio ?? null : 1
  );

  /** En Pesos el tipo de cambio es fijo en 1 y no se edita — solo tiene
   * sentido cargarlo cuando la moneda es Dólares. */
  function setMoneda(nuevaMoneda: MonedaCompra) {
    setMonedaState(nuevaMoneda);
    if (nuevaMoneda === "Pesos") setTipoDeCambio(1);
    else if (tipoDeCambio === 1) setTipoDeCambio(null);
  }
  const [ajustaTipoCambio, setAjustaTipoCambio] = useState(initial?.ajustaTipoCambio ?? false);
  const [documentoOriginalLink, setDocumentoOriginalLink] = useState(initial?.documentoOriginal ?? "");
  const [conceptos, setConceptos] = useState({
    ingresosBrutos: initial?.ingresosBrutos ?? 0,
    conceptosNoGravados: initial?.conceptosNoGravados ?? 0,
    guias: initial?.guias ?? 0,
    comision: initial?.comision ?? 0,
    financiacion: initial?.financiacion ?? 0,
    gastosVarios: initial?.gastosVarios ?? 0,
    leyDeSellos: initial?.leyDeSellos ?? 0,
    resGral4169: initial?.resGral4169 ?? 0,
  });

  const [rows, setRows] = useState<GridRow[]>(() => {
    if (initial?.lineas.length) {
      const iniciales = initial.lineas.map(lineaARow);
      const relleno = Math.max(0, FILAS_INICIALES - iniciales.length);
      return [...iniciales, ...Array.from({ length: relleno }, () => ({ ...FILA_VACIA }))];
    }
    const vacias = Array.from({ length: FILAS_INICIALES }, () => ({ ...FILA_VACIA }));
    if (prefill?.importe) {
      // Una sola línea con el importe del consumo (sin IVA discriminado): el usuario la ajusta.
      vacias[0] = {
        ...vacias[0],
        cantidad: "1",
        productoServicio: prefill.detalle ?? "",
        precioUnitario: numeroAEdicionLocal(prefill.importe),
        iva: "0",
      };
    }
    return vacias;
  });

  const [vencimientos, setVencimientos] = useState<VencimientoInput[]>(
    initial?.vencimientos.map(({ fechaVencimiento }) => ({ fechaVencimiento })) ?? []
  );
  const [condicionPago, setCondicionPago] = useState<"Contado" | "A Plazo">(
    initial?.vencimientos.length ? "A Plazo" : "Contado"
  );

  function handleCondicionPagoChange(valor: "Contado" | "A Plazo") {
    setCondicionPago(valor);
    if (valor === "Contado") {
      setVencimientos([]);
    } else if (vencimientos.length === 0) {
      setVencimientos([{ fechaVencimiento: "" }]);
    }
  }

  // Rubro/Centro de Costos/Destino de las líneas existentes llegan como id
  // (data-model.md) — se resuelven a texto para la grilla recién cuando los
  // catálogos terminan de cargar (efecto separado, corre una sola vez).
  useEffect(() => {
    if (!filtros || !initial?.lineas.length) return;
    setRows((prev) =>
      prev.map((row, i) => {
        const linea = initial.lineas[i];
        if (!linea) return row;
        return {
          ...row,
          rubro: row.rubro || filtros.rubros.find((r) => r.idRubro === linea.idRubro)?.rubro || "",
          centroCosto:
            row.centroCosto ||
            filtros.centrosCosto.find((c) => c.idCentroCosto === linea.idCentroCosto)?.centroCosto ||
            "",
          destino:
            row.destino || filtros.destinos.find((d) => d.idDestino === linea.idDestino)?.destino || "",
        };
      })
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtros]);

  const [isSaving, setIsSaving] = useState(false);
  const [lockToken] = useState(() => generarUuid());
  const [lockError, setLockError] = useState<string | null>(null);

  // Documentos relacionados (ej. Nota de Crédito/Débito que complementa esta
  // Factura): lista → selección manual del usuario. En alta se guardan
  // "pendientes" hasta que la compra tenga un id real; en edición se
  // vinculan/desvinculan al toque contra `WC`.
  const relacionadosKey = ["compras-relacionados", idCompra];
  const { data: relacionadosGuardados } = useQuery({
    queryKey: relacionadosKey,
    queryFn: () => fetchDocumentosRelacionados(idCompra!),
    enabled: mode === "edicion" && idCompra != null,
  });
  const [relacionadosPendientes, setRelacionadosPendientes] = useState<DocumentoRelacionado[]>([]);

  const relacionadosMostrados = mode === "edicion" ? relacionadosGuardados ?? [] : relacionadosPendientes;

  async function handleVincularRelacionado(doc: DocumentoRelacionado) {
    if (mode === "alta" || idCompra == null) {
      setRelacionadosPendientes((prev) => [...prev, doc]);
      return;
    }
    try {
      await agregarDocumentoRelacionado(idCompra, doc.idCompra);
      queryClient.invalidateQueries({ queryKey: relacionadosKey });
      showToast("Documento vinculado.", "success");
    } catch {
      showToast("No se pudo vincular el documento.", "danger");
    }
  }

  async function handleDesvincularRelacionado(idCompraRelacionada: number) {
    if (mode === "alta" || idCompra == null) {
      setRelacionadosPendientes((prev) => prev.filter((d) => d.idCompra !== idCompraRelacionada));
      return;
    }
    try {
      await quitarDocumentoRelacionado(idCompra, idCompraRelacionada);
      queryClient.invalidateQueries({ queryKey: relacionadosKey });
      showToast("Vínculo quitado.", "neutral");
    } catch {
      showToast("No se pudo quitar el vínculo.", "danger");
    }
  }

  const lineasCalculadas = rows.map(calcularLinea);
  const subtotalNeto = lineasCalculadas.reduce((acc, l) => acc + l.subtotal, 0);
  const ivaLineas = lineasCalculadas.reduce((acc, l) => acc + l.importeIva, 0);
  const accesorios = conceptos.comision + conceptos.guias + conceptos.financiacion + conceptos.gastosVarios;
  const ivaCabecera = ivaLineas + 0.105 * accesorios;
  const importeTotal =
    subtotalNeto +
    ivaCabecera +
    conceptos.ingresosBrutos +
    conceptos.conceptosNoGravados +
    conceptos.guias +
    conceptos.comision +
    conceptos.financiacion +
    conceptos.gastosVarios +
    conceptos.leyDeSellos +
    conceptos.resGral4169;
  const importePesificado = moneda === "Dolares" && tipoDeCambio ? importeTotal * tipoDeCambio : null;

  const lockIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [forzandoLock, setForzandoLock] = useState(false);

  async function handleForzarLock() {
    if (idCompra == null) return;
    setForzandoLock(true);
    try {
      await adquirirLock(idCompra, lockToken, true);
      setLockError(null);
    } catch {
      showToast("No se pudo forzar la edición. Intentá de nuevo.", "danger");
    } finally {
      setForzandoLock(false);
    }
  }

  useEffect(() => {
    if (mode !== "edicion" || idCompra == null) return;

    let cancelado = false;
    async function adquirir() {
      try {
        await adquirirLock(idCompra!, lockToken);
        if (!cancelado) setLockError(null);
      } catch {
        if (!cancelado) {
          setLockError(
            "Esta compra está siendo editada en otra sesión. Si sabés que sos vos mismo " +
              "(otra pestaña, o quedó colgada de antes), podés forzar la edición."
          );
        }
      }
    }
    // El lock expira a los 5 minutos (LOCK_TTL_MINUTES) — se renueva bastante
    // antes para no perderlo en una sesión de edición activa.
    adquirir();
    lockIntervalRef.current = setInterval(adquirir, 2 * 60 * 1000);

    // Liberación al cerrar/navegar fuera de la pestaña: el cleanup normal
    // de React de abajo puede no llegar a completarse en un cierre abrupto
    // (el fetch se cancela junto con la página) — `pagehide` + `keepalive`
    // deja la petición de liberación sobrevivir a ese cierre.
    function liberarAlSalir() {
      liberarLock(idCompra!, lockToken, true).catch(() => {});
    }
    window.addEventListener("pagehide", liberarAlSalir);

    return () => {
      cancelado = true;
      if (lockIntervalRef.current) clearInterval(lockIntervalRef.current);
      window.removeEventListener("pagehide", liberarAlSalir);
      liberarLock(idCompra!, lockToken).catch(() => {});
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, idCompra]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (idContacto == null) {
      showToast("Seleccioná un proveedor.", "danger");
      return;
    }
    const lineas = filasARequestLineas(rows, filtros);
    if (lineas.length === 0) {
      showToast("Agregá al menos una línea.", "danger");
      return;
    }
    if (moneda === "Dolares" && (!tipoDeCambio || tipoDeCambio <= 0)) {
      showToast("El tipo de cambio es obligatorio para compras en Dólares.", "danger");
      return;
    }
    const vencimientosCompletos = vencimientos.filter((v) => v.fechaVencimiento);
    if (condicionPago === "A Plazo" && vencimientosCompletos.length === 0) {
      showToast("Cargá al menos una fecha de vencimiento, o cambiá la condición a Contado.", "danger");
      return;
    }

    const input: CompraAltaInput = {
      idContacto,
      fecha,
      tipo,
      tipoDocumento,
      numeroDocumento,
      moneda,
      tipoDeCambio: moneda === "Dolares" ? tipoDeCambio : 1,
      ajustaTipoCambio,
      documentoOriginal: documentoOriginalLink ? limpiarRutaCopiada(documentoOriginalLink) : null,
      ...conceptos,
      lineas,
      vencimientos: vencimientosCompletos,
    };

    setIsSaving(true);
    try {
      const resultado =
        mode === "alta" ? await crearCompra(input) : await actualizarCompra(idCompra!, input, lockToken);

      if (mode === "alta" && relacionadosPendientes.length > 0) {
        await Promise.all(
          relacionadosPendientes.map((doc) =>
            agregarDocumentoRelacionado(resultado.idCompra, doc.idCompra).catch(() => {})
          )
        );
      }

      resultado.warnings.forEach((w) => showToast(w, "neutral"));
      showToast(mode === "alta" ? "Compra creada." : "Compra actualizada.", "success");
      if (mode === "edicion" && idCompra != null) {
        await liberarLock(idCompra, lockToken).catch(() => {});
      }
      router.push("/compras");
    } catch (err) {
      const mensaje =
        err instanceof ApiError && err.status === 400 && err.message
          ? err.message
          : "No se pudo guardar la compra. Revisá los datos e intentá de nuevo.";
      showToast(mensaje, "danger");
    } finally {
      setIsSaving(false);
    }
  }

  const [eliminando, setEliminando] = useState(false);

  async function handleEliminar() {
    if (idCompra == null) return;
    if (!window.confirm("¿Eliminar esta compra? Esta acción no se puede deshacer.")) return;
    setEliminando(true);
    try {
      await eliminarCompra(idCompra, lockToken);
      showToast("Compra eliminada.", "success");
      router.push("/compras");
    } catch (err) {
      const mensaje =
        err instanceof ApiError && err.message
          ? err.message
          : "No se pudo eliminar la compra. Intentá de nuevo.";
      showToast(mensaje, "danger");
      setEliminando(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-2"
      style={{ height: "calc(100vh - 8rem)" }}
      // Mitiga falsos "Hydration failed" causados por extensiones del
      // navegador (gestores de contraseñas, Grammarly, etc.) que inyectan
      // atributos en <form>/<input> antes de que React hidrate — causa
      // documentada y común de este error, no un bug de la app.
      suppressHydrationWarning
    >
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

      {/* Encabezado fijo: grid que reparte los campos por todo el ancho
          disponible (en vez de agruparlos a la izquierda) — cuantas más
          columnas entran por fila, menos filas ocupa el encabezado. */}
      <div className="shrink-0 space-y-2">
        <div className="grid grid-cols-[repeat(auto-fit,minmax(10rem,1fr))] items-end gap-2 rounded-md border border-border bg-surface p-2">
          <div className="sm:col-span-2">
            <ContactoSelect
              label="Proveedor"
              tipoContacto={TIPOS_CONTACTO_COMPRA}
              value={idContacto}
              razonSocial={razonSocialProveedor}
              onChange={(id, nombre) => {
                setIdContacto(id);
                setRazonSocialProveedor(nombre);
              }}
              placeholder="Buscar proveedor…"
            />
          </div>
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
          <label className={labelCompacto}>
            Tipo
            <select className={inputCompacto} value={tipo} onChange={(e) => setTipo(e.target.value as TipoComprobante)}>
              {TIPOS_COMPROBANTE.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <label className={labelCompacto}>
            Tipo de documento
            <select
              className={inputCompacto}
              value={tipoDocumento}
              onChange={(e) => setTipoDocumento(e.target.value as TipoDocumentoCompra)}
            >
              {TIPOS_DOCUMENTO.map((t) => (
                <option key={t} value={t}>
                  {t}
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
              onChange={(e) => setNumeroDocumento(e.target.value.replace(/\s*-\s*/g, "-").slice(0, 15))}
              placeholder="0001-00012345"
            />
          </label>
          <label className={labelCompacto}>
            Moneda
            <select
              className={inputCompacto}
              value={moneda}
              onChange={(e) => setMoneda(e.target.value as MonedaCompra)}
            >
              <option value="Pesos">Pesos</option>
              <option value="Dolares">Dólares</option>
            </select>
          </label>
          <label className={labelCompacto}>
            Tipo de cambio
            <input
              type="number"
              required={moneda === "Dolares"}
              disabled={moneda !== "Dolares"}
              className={`${inputCompacto} disabled:cursor-not-allowed disabled:opacity-60`}
              value={moneda === "Dolares" ? tipoDeCambio ?? "" : 1}
              onChange={(e) => setTipoDeCambio(e.target.value ? Number(e.target.value) : null)}
              placeholder={moneda === "Dolares" ? "Obligatorio" : undefined}
            />
          </label>
          <label className="flex items-center gap-1.5 self-center text-xs text-ink-secondary">
            <input
              type="checkbox"
              checked={ajustaTipoCambio}
              onChange={(e) => setAjustaTipoCambio(e.target.checked)}
            />
            Ajusta tipo de cambio
          </label>
          <label className="sm:col-span-2">
            <span className="text-xs text-ink-secondary">Documento original (PDF)</span>
            <div className="flex items-center gap-1">
              <input
                className={inputCompacto}
                value={documentoOriginalLink}
                onChange={(e) => setDocumentoOriginalLink(e.target.value)}
                placeholder="Link o ruta al PDF escaneado…"
              />
              {documentoOriginalLink && (
                <a
                  href={urlParaAbrirDocumento(documentoOriginalLink, BASE_DOCUMENTOS_COMPRAS, urlDocumentoLocal)}
                  target="_blank"
                  rel="noreferrer"
                  title={
                    esRutaLocalWindows(documentoOriginalLink, BASE_DOCUMENTOS_COMPRAS)
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

        <DocumentosRelacionadosPanel
          idContacto={idContacto}
          tipoDocumento={tipoDocumento}
          relacionados={relacionadosMostrados}
          onVincular={handleVincularRelacionado}
          onDesvincular={handleDesvincularRelacionado}
          excluirIdCompra={idCompra}
        />
      </div>

      {/* Cuerpo: única sección que scrollea. */}
      <div className="min-h-0 flex-1 overflow-y-auto">
        <ComprasGrid
          rows={rows}
          onChange={setRows}
          filtros={filtros}
          moneda={moneda}
          onCatalogoActualizado={() => refetchFiltros()}
        />
      </div>

      {/* Pie fijo, igual que una factura física: vencimientos + conceptos a
          la izquierda, totales acumulados a la derecha. */}
      <div className="shrink-0 space-y-2">
        <div className="flex flex-wrap items-center gap-3 rounded-md border border-border bg-surface p-2 text-xs">
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-1 text-ink-secondary">
              <input
                type="radio"
                name="condicionPago"
                checked={condicionPago === "Contado"}
                onChange={() => handleCondicionPagoChange("Contado")}
              />
              Contado
            </label>
            <label className="flex items-center gap-1 text-ink-secondary">
              <input
                type="radio"
                name="condicionPago"
                checked={condicionPago === "A Plazo"}
                onChange={() => handleCondicionPagoChange("A Plazo")}
              />
              A Plazo
            </label>
          </div>
          {condicionPago === "A Plazo" && (
            <VencimientosEditor vencimientos={vencimientos} onChange={setVencimientos} />
          )}
        </div>

        <div className="flex flex-col gap-2 rounded-md border border-border bg-surface-sunken p-2 xl:flex-row xl:items-start xl:justify-between">
          <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs">
            {(
              [
                ["ingresosBrutos", "Ingresos Brutos"],
                ["conceptosNoGravados", "Conceptos no gravados"],
                ["guias", "Guías"],
                ["comision", "Comisión"],
                ["financiacion", "Financiación"],
                ["gastosVarios", "Gastos Varios"],
                ["leyDeSellos", "Ley de Sellos"],
                ["resGral4169", "Res. Gral. 4169/96"],
              ] as const
            ).map(([key, label]) => (
              <label key={key} className="flex flex-col gap-0.5 text-ink-secondary">
                {label}
                <MoneyInput
                  className={`${inputCompacto} w-24 text-right font-data`}
                  value={conceptos[key]}
                  moneda={moneda}
                  onChange={(v) => setConceptos({ ...conceptos, [key]: v })}
                />
              </label>
            ))}
          </div>

          <div className="min-w-[14rem] space-y-0.5 text-right text-xs xl:border-l xl:border-border xl:pl-4">
            <p className="font-data text-ink-secondary">
              Subtotal neto: <span className="text-ink-primary">{formatMoneda(subtotalNeto, moneda)}</span>
            </p>
            <p className="font-data text-ink-secondary">
              IVA: <span className="text-ink-primary">{formatMoneda(ivaCabecera, moneda)}</span>
            </p>
            {moneda === "Dolares" ? (
              <>
                <p className="font-data text-sm font-semibold text-ink-primary">
                  Importe total: {formatMoneda(importeTotal, "Dolares")}
                </p>
                {importePesificado != null && (
                  <p className="font-data text-ink-secondary">
                    Equivalente en pesos (TC {tipoDeCambio}): {formatMoneda(importePesificado, "Pesos")}
                  </p>
                )}
              </>
            ) : (
              <p className="font-data text-sm font-semibold text-ink-primary">
                Importe total: {formatMoneda(importeTotal, "Pesos")}
              </p>
            )}
          </div>
        </div>

        <div className="flex justify-between gap-2">
          {mode === "edicion" ? (
            <button
              type="button"
              onClick={handleEliminar}
              disabled={eliminando || isSaving || lockError != null}
              title={lockError ?? "Eliminar esta compra (ej. cargada por error). No se puede deshacer."}
              className="rounded-sm border border-status-danger px-3 py-1.5 text-xs text-status-danger hover:bg-status-danger-bg disabled:opacity-40"
            >
              {eliminando ? "Eliminando…" : "Eliminar compra"}
            </button>
          ) : (
            <span />
          )}
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => router.push("/compras")}
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
