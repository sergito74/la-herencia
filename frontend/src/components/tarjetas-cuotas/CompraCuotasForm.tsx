"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import {
  actualizarCompra,
  adquirirLockCompra,
  crearCompra,
  eliminarCompra,
  liberarLockCompra,
  marcarCobrada,
  type CompraCuotasAltaInput,
  type CompraCuotasDetalle,
  type Cuota,
} from "@/services/tarjetasCuotasApi";
import { ApiError } from "@/services/apiClient";
import { formatMoneda } from "@/lib/format";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { MoneyInput } from "@/components/ui/MoneyInput";
import { filterInputClass } from "@/components/ui/FilterBar";
import { useToast } from "@/components/ui/Toast";

const inputCompacto = `${filterInputClass} w-full px-1.5 py-1 text-xs`;
const labelCompacto = "flex flex-col gap-0.5 text-xs text-ink-secondary";

function generarUuid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

/** Alta/edición de Compra en Cuotas (Historia 3) — no vinculada a una
 * tarjeta del catálogo (data-model.md). Editar importe/cantidad regenera
 * el cronograma completo y pierde el estado "cobrado" de las cuotas
 * anteriores (FR-007a, Clarifications 2026-09-18). */
export function CompraCuotasForm({
  mode,
  idPagoTarjeta,
  initial,
}: {
  mode: "alta" | "edicion";
  idPagoTarjeta?: number;
  initial?: CompraCuotasDetalle;
}) {
  const router = useRouter();
  const { showToast } = useToast();

  const [idContacto, setIdContacto] = useState<number | null>(initial?.idContacto ?? null);
  const [contactoNombre, setContactoNombre] = useState<string | null>(initial?.contacto ?? null);
  const [fecha, setFecha] = useState(initial?.fecha ?? "");
  const [nroComprobante, setNroComprobante] = useState<number | "">(initial?.nroComprobante ?? "");
  const [importeTotal, setImporteTotal] = useState(initial?.importeTotal ?? 0);
  const [cantidadCuotas, setCantidadCuotas] = useState(initial?.cantidadCuotas ?? 1);
  const [cuotasGeneradas, setCuotasGeneradas] = useState<Cuota[]>(initial?.cuotas ?? []);

  const [isSaving, setIsSaving] = useState(false);
  const [lockToken] = useState(() => generarUuid());
  const [lockError, setLockError] = useState<string | null>(null);
  const [forzandoLock, setForzandoLock] = useState(false);
  const lockIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  async function handleForzarLock() {
    if (idPagoTarjeta == null) return;
    setForzandoLock(true);
    try {
      await adquirirLockCompra(idPagoTarjeta, lockToken, true);
      setLockError(null);
    } catch {
      showToast("No se pudo forzar la edición. Intentá de nuevo.", "danger");
    } finally {
      setForzandoLock(false);
    }
  }

  useEffect(() => {
    if (mode !== "edicion" || idPagoTarjeta == null) return;

    let cancelado = false;
    async function adquirir() {
      try {
        await adquirirLockCompra(idPagoTarjeta!, lockToken);
        if (!cancelado) setLockError(null);
      } catch {
        if (!cancelado) {
          setLockError(
            "Esta compra está siendo editada en otra sesión. Si sabés que sos vos mismo, podés forzar la edición."
          );
        }
      }
    }
    adquirir();
    lockIntervalRef.current = setInterval(adquirir, 2 * 60 * 1000);

    function liberarAlSalir() {
      liberarLockCompra(idPagoTarjeta!, lockToken, true).catch(() => {});
    }
    window.addEventListener("pagehide", liberarAlSalir);

    return () => {
      cancelado = true;
      if (lockIntervalRef.current) clearInterval(lockIntervalRef.current);
      window.removeEventListener("pagehide", liberarAlSalir);
      liberarLockCompra(idPagoTarjeta!, lockToken).catch(() => {});
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, idPagoTarjeta]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (idContacto == null) {
      showToast("Seleccioná un contacto.", "danger");
      return;
    }
    if (!nroComprobante) {
      showToast("Ingresá el número de comprobante.", "danger");
      return;
    }

    const input: CompraCuotasAltaInput = {
      idContacto,
      fecha,
      nroComprobante: Number(nroComprobante),
      importeTotal,
      cantidadCuotas,
    };

    setIsSaving(true);
    try {
      const resultado =
        mode === "alta" ? await crearCompra(input) : await actualizarCompra(idPagoTarjeta!, input, lockToken);

      setCuotasGeneradas(resultado.cuotas);
      showToast(mode === "alta" ? "Compra en cuotas creada." : "Compra en cuotas actualizada.", "success");
      if (mode === "edicion" && idPagoTarjeta != null) {
        await liberarLockCompra(idPagoTarjeta, lockToken).catch(() => {});
      }
      router.push("/finanzas/tarjetas/compras-en-cuotas");
    } catch (err) {
      const mensaje =
        err instanceof ApiError && err.status === 400 && err.message
          ? err.message
          : "No se pudo guardar la compra en cuotas. Revisá los datos e intentá de nuevo.";
      showToast(mensaje, "danger");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleToggleCobrada(cuota: Cuota) {
    if (idPagoTarjeta == null) return;
    try {
      const actualizada = await marcarCobrada(idPagoTarjeta, cuota.idCuota, !cuota.cobrado);
      setCuotasGeneradas((prev) => prev.map((c) => (c.idCuota === cuota.idCuota ? actualizada : c)));
    } catch {
      showToast("No se pudo actualizar el estado de la cuota.", "danger");
    }
  }

  const [eliminando, setEliminando] = useState(false);

  async function handleEliminar() {
    if (idPagoTarjeta == null) return;
    if (!window.confirm("¿Eliminar esta compra en cuotas? Esta acción no se puede deshacer.")) return;
    setEliminando(true);
    try {
      await eliminarCompra(idPagoTarjeta, lockToken);
      showToast("Compra en cuotas eliminada.", "success");
      router.push("/finanzas/tarjetas/compras-en-cuotas");
    } catch (err) {
      const mensaje = err instanceof ApiError && err.message ? err.message : "No se pudo eliminar la compra.";
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

      {mode === "edicion" && (
        <div className="rounded-sm border border-status-warning bg-status-warning-bg px-2 py-1 text-xs text-status-warning">
          Cambiar el importe total o la cantidad de cuotas regenera todo el cronograma — las cuotas ya marcadas como
          cobradas vuelven a quedar pendientes (FR-007a).
        </div>
      )}

      <div className="grid grid-cols-[repeat(auto-fit,minmax(10rem,1fr))] items-end gap-2 rounded-md border border-border bg-surface p-2">
        <div className="sm:col-span-2">
          <ContactoSelect
            label="Contacto"
            value={idContacto}
            razonSocial={contactoNombre}
            onChange={(id, nombre) => {
              setIdContacto(id);
              setContactoNombre(nombre);
            }}
            placeholder="Buscar contacto…"
          />
        </div>
        <label className={labelCompacto}>
          Fecha
          <input type="date" required className={inputCompacto} value={fecha} onChange={(e) => setFecha(e.target.value)} />
        </label>
        <label className={labelCompacto}>
          Nº comprobante
          <input
            type="number"
            required
            className={inputCompacto}
            value={nroComprobante}
            onChange={(e) => setNroComprobante(e.target.value ? Number(e.target.value) : "")}
          />
        </label>
        <label className={labelCompacto}>
          Importe total
          <MoneyInput className={`${inputCompacto} text-right font-data`} value={importeTotal} moneda="Pesos" onChange={setImporteTotal} />
        </label>
        <label className={labelCompacto}>
          Cantidad de cuotas
          <input
            type="number"
            min={1}
            required
            className={`${inputCompacto} text-right font-data`}
            value={cantidadCuotas}
            onChange={(e) => setCantidadCuotas(Math.max(1, Number(e.target.value) || 1))}
          />
        </label>
      </div>

      {cuotasGeneradas.length > 0 && (
        <div className="rounded-md border border-border bg-surface p-2">
          <h3 className="text-xs font-medium text-ink-secondary">Cronograma de cuotas</h3>
          <table className="mt-1 w-full text-xs">
            <thead>
              <tr className="text-left text-ink-secondary">
                <th className="py-1">Cuota</th>
                <th className="py-1">Vencimiento</th>
                <th className="py-1 text-right">Importe</th>
                <th className="py-1 text-right">Estado</th>
              </tr>
            </thead>
            <tbody>
              {cuotasGeneradas.map((c) => (
                <tr key={c.idCuota} className="border-t border-border">
                  <td className="py-1">{c.numeroCuota}</td>
                  <td className="py-1">{c.fechaVencimiento}</td>
                  <td className="py-1 text-right font-data">{formatMoneda(c.importe)}</td>
                  <td className="py-1 text-right">
                    <button
                      type="button"
                      onClick={() => handleToggleCobrada(c)}
                      className={
                        c.cobrado
                          ? "rounded-sm border border-status-success px-2 py-0.5 text-status-success"
                          : "rounded-sm border border-border px-2 py-0.5 text-ink-secondary hover:text-ink-primary"
                      }
                    >
                      {c.cobrado ? "Cobrada" : "Pendiente"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex justify-between gap-2">
        {mode === "edicion" ? (
          <button
            type="button"
            onClick={handleEliminar}
            disabled={eliminando || isSaving || lockError != null}
            title={lockError ?? "Eliminar esta compra en cuotas. No se puede deshacer."}
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
            onClick={() => router.push("/finanzas/tarjetas/compras-en-cuotas")}
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
