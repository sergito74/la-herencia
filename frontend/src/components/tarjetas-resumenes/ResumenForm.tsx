"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { useEffect, useRef, useState } from "react";

import {
  actualizarResumen,
  adquirirLockResumen,
  crearResumen,
  eliminarResumen,
  liberarLockResumen,
  type LineaConsumoInput,
  type ResumenAltaInput,
  type ResumenDetalle,
} from "@/services/tarjetasResumenesApi";
import { fetchTarjetas } from "@/services/tarjetasApi";
import { ApiError } from "@/services/apiClient";
import { formatMoneda } from "@/lib/format";
import { ArchivoVinculado } from "@/components/ui/ArchivoVinculado";
import { MoneyInput } from "@/components/ui/MoneyInput";
import { filterInputClass } from "@/components/ui/FilterBar";
import { useToast } from "@/components/ui/Toast";
import { LineasConsumoEditor } from "@/components/tarjetas-resumenes/LineasConsumoEditor";

const inputCompacto = `${filterInputClass} w-full px-1.5 py-1 text-xs`;
const labelCompacto = "flex flex-col gap-0.5 text-xs text-ink-secondary";

const CARGOS: [keyof ResumenAltaInput, string][] = [
  ["impuestoSellos", "Impuesto de Sellos"],
  ["gastosAdmin", "Gastos de Administración"],
  ["mantCuenta", "Mantenimiento de Cuenta"],
  ["renovAnual", "Renovación Anual"],
  ["promocionBNA", "Promoción BNA"],
  ["creditoContingente", "Crédito Contingente"],
  ["intFinanc", "Interés de Financiación"],
  ["intCompens", "Interés Compensatorio"],
  ["iva105", "IVA 10,5%"],
  ["percepIVA105", "Percepción IVA 10,5%"],
  ["iva21", "IVA 21%"],
  ["percepIVA21", "Percepción IVA 21%"],
  ["percepIIBB", "Percepción IIBB"],
  ["ajusteResAnterior", "Ajuste de Resumen Anterior"],
];

function generarUuid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

/** Alta/edición de Resumen de Tarjeta (Historia 1) — cabecera con 14
 * cargos/impuestos (FR-008) + grilla de líneas de consumo, con o sin
 * líneas ("solo cabecera", FR-009). Modo edición usa el mismo mecanismo
 * de bloqueo exclusivo que Compras/Ventas. */
export function ResumenForm({
  mode,
  idResumen,
  initial,
}: {
  mode: "alta" | "edicion";
  idResumen?: number;
  initial?: ResumenDetalle;
}) {
  const router = useRouter();
  const { showToast } = useToast();

  const { data: tarjetas } = useQuery({
    queryKey: ["tarjetas", "activas-o-actual"],
    queryFn: () => fetchTarjetas(false),
    staleTime: Infinity,
  });

  const [idTarjeta, setIdTarjeta] = useState<string>(initial?.idTarjeta ? String(initial.idTarjeta) : "");
  const [codigo, setCodigo] = useState(initial?.codigo ?? "");
  const [fechaCierre, setFechaCierre] = useState(initial?.fechaCierre ?? "");
  const [fechaVencimiento, setFechaVencimiento] = useState(initial?.fechaVencimiento ?? "");
  const [urlResumenOriginal, setUrlResumenOriginal] = useState(initial?.urlResumenOriginal ?? "");
  const [cargos, setCargos] = useState<Record<string, number>>(() => {
    const base: Record<string, number> = {};
    for (const [key] of CARGOS) base[key] = (initial?.[key] as number) ?? 0;
    return base;
  });
  const [lineas, setLineas] = useState<LineaConsumoInput[]>(
    initial?.lineas.map((l) => ({
      fechaCompra: l.fechaCompra,
      detalle: l.detalle,
      importe: l.importe,
      fechaVencimientoCompra: l.fechaVencimientoCompra ?? null,
      idContacto: l.idContacto ?? null,
      nroDocumento: l.nroDocumento ?? null,
    })) ?? []
  );

  const [isSaving, setIsSaving] = useState(false);
  const [lockToken] = useState(() => generarUuid());
  const [lockError, setLockError] = useState<string | null>(null);
  const [forzandoLock, setForzandoLock] = useState(false);
  const lockIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const totalCalculado =
    lineas.reduce((acc, l) => acc + (l.importe || 0), 0) +
    CARGOS.reduce((acc, [key]) => acc + (cargos[key] || 0), 0);

  async function handleForzarLock() {
    if (idResumen == null) return;
    setForzandoLock(true);
    try {
      await adquirirLockResumen(idResumen, lockToken, true);
      setLockError(null);
    } catch {
      showToast("No se pudo forzar la edición. Intentá de nuevo.", "danger");
    } finally {
      setForzandoLock(false);
    }
  }

  useEffect(() => {
    if (mode !== "edicion" || idResumen == null) return;

    let cancelado = false;
    async function adquirir() {
      try {
        await adquirirLockResumen(idResumen!, lockToken);
        if (!cancelado) setLockError(null);
      } catch {
        if (!cancelado) {
          setLockError(
            "Este resumen está siendo editado en otra sesión. Si sabés que sos vos mismo, podés forzar la edición."
          );
        }
      }
    }
    adquirir();
    lockIntervalRef.current = setInterval(adquirir, 2 * 60 * 1000);

    function liberarAlSalir() {
      liberarLockResumen(idResumen!, lockToken, true).catch(() => {});
    }
    window.addEventListener("pagehide", liberarAlSalir);

    return () => {
      cancelado = true;
      if (lockIntervalRef.current) clearInterval(lockIntervalRef.current);
      window.removeEventListener("pagehide", liberarAlSalir);
      liberarLockResumen(idResumen!, lockToken).catch(() => {});
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, idResumen]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!idTarjeta) {
      showToast("Seleccioná una tarjeta.", "danger");
      return;
    }

    const input: ResumenAltaInput = {
      idTarjeta: Number(idTarjeta),
      codigo,
      fechaCierre,
      fechaVencimiento,
      urlResumenOriginal: urlResumenOriginal || null,
      ...cargos,
      lineas,
    };

    setIsSaving(true);
    try {
      const resultado =
        mode === "alta" ? await crearResumen(input) : await actualizarResumen(idResumen!, input, lockToken);

      resultado.warnings.forEach((w) => showToast(w, "neutral"));
      showToast(mode === "alta" ? "Resumen creado." : "Resumen actualizado.", "success");
      if (mode === "edicion" && idResumen != null) {
        await liberarLockResumen(idResumen, lockToken).catch(() => {});
      }
      router.push("/finanzas/tarjetas/resumenes");
    } catch (err) {
      const mensaje =
        err instanceof ApiError && err.status === 400 && err.message
          ? err.message
          : "No se pudo guardar el resumen. Revisá los datos e intentá de nuevo.";
      showToast(mensaje, "danger");
    } finally {
      setIsSaving(false);
    }
  }

  const [eliminando, setEliminando] = useState(false);

  async function handleEliminar() {
    if (idResumen == null) return;
    if (!window.confirm("¿Eliminar este resumen? Esta acción no se puede deshacer.")) return;
    setEliminando(true);
    try {
      await eliminarResumen(idResumen, lockToken);
      showToast("Resumen eliminado.", "success");
      router.push("/finanzas/tarjetas/resumenes");
    } catch (err) {
      const mensaje = err instanceof ApiError && err.message ? err.message : "No se pudo eliminar el resumen.";
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
        <label className={labelCompacto}>
          Tarjeta
          <select className={inputCompacto} value={idTarjeta} onChange={(e) => setIdTarjeta(e.target.value)} required>
            <option value="">—</option>
            {tarjetas
              ?.filter((t) => t.activa || String(t.idTarjeta) === idTarjeta)
              .map((t) => (
                <option key={t.idTarjeta} value={t.idTarjeta}>
                  {t.nombre} {!t.activa && "(inactiva)"}
                </option>
              ))}
          </select>
        </label>
        <label className={labelCompacto}>
          Código
          <input required className={inputCompacto} value={codigo} onChange={(e) => setCodigo(e.target.value.slice(0, 80))} />
        </label>
        <label className={labelCompacto}>
          Fecha de cierre
          <input type="date" required className={inputCompacto} value={fechaCierre} onChange={(e) => setFechaCierre(e.target.value)} />
        </label>
        <label className={labelCompacto}>
          Fecha de vencimiento
          <input
            type="date"
            required
            className={inputCompacto}
            value={fechaVencimiento}
            onChange={(e) => setFechaVencimiento(e.target.value)}
          />
        </label>
        <ArchivoVinculado
          className="sm:col-span-2"
          label="Resumen original (PDF)"
          value={urlResumenOriginal}
          onChange={setUrlResumenOriginal}
          inputClassName={inputCompacto}
        />
      </div>

      <div className="grid grid-cols-[repeat(auto-fit,minmax(9rem,1fr))] gap-2 rounded-md border border-border bg-surface p-2">
        {CARGOS.map(([key, label]) => (
          <label key={key} className={labelCompacto}>
            {label}
            <MoneyInput
              className={`${inputCompacto} text-right font-data`}
              value={cargos[key] ?? 0}
              moneda="Pesos"
              onChange={(v) => setCargos((prev) => ({ ...prev, [key]: v }))}
            />
          </label>
        ))}
      </div>

      <LineasConsumoEditor lineas={lineas} onChange={setLineas} />

      <div className="flex items-center justify-end gap-2 rounded-md border border-border bg-surface-sunken p-2">
        <p className="font-data text-sm font-semibold text-ink-primary">Total calculado: {formatMoneda(totalCalculado)}</p>
      </div>

      <div className="flex justify-between gap-2">
        {mode === "edicion" ? (
          <button
            type="button"
            onClick={handleEliminar}
            disabled={eliminando || isSaving || lockError != null}
            title={lockError ?? "Eliminar este resumen. No se puede deshacer."}
            className="rounded-sm border border-status-danger px-3 py-1.5 text-xs text-status-danger hover:bg-status-danger-bg disabled:opacity-40"
          >
            {eliminando ? "Eliminando…" : "Eliminar resumen"}
          </button>
        ) : (
          <span />
        )}
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={() => router.push("/finanzas/tarjetas/resumenes")}
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
