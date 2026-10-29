"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import {
  crearLiquidacion,
  actualizarLiquidacion,
  fetchLiquidacion,
  subirRecibo,
  type NuevaLiquidacionRequest,
} from "@/services/remuneracionesApi";
import { ApiError } from "@/services/apiClient";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { filterInputClass } from "@/components/ui/FilterBar";
import { MoneyInput } from "@/components/ui/MoneyInput";
import { useToast } from "@/components/ui/Toast";
import { formatMoneda } from "@/lib/format";
import { AdicionalSierra } from "@/components/remuneraciones/AdicionalSierra";

const HABERES: { campo: keyof NuevaLiquidacionRequest; label: string }[] = [
  { campo: "sueldoBasico", label: "Sueldo básico" },
  { campo: "antiguedad", label: "Antigüedad" },
  { campo: "adicFuturosAumentos", label: "Adic. futuros aumentos" },
  { campo: "diaGremio", label: "Día Gremio" },
  { campo: "aguinaldo", label: "Aguinaldo" },
  { campo: "vacaciones", label: "Vacaciones" },
  { campo: "ajuste", label: "Ajuste" },
  { campo: "ajusteNoRemunerativo", label: "Ajuste No Remunerativo" },
  { campo: "redondeo", label: "Redondeo" },
  { campo: "bonificacionAdicional", label: "Bonificación adicional" },
];

const DESCUENTOS: { campo: keyof NuevaLiquidacionRequest; label: string }[] = [
  { campo: "jubilacion", label: "Jubilación" },
  { campo: "ley19032", label: "Ley 19032" },
  { campo: "obraSocial", label: "Obra Social" },
  { campo: "obraSocialAcuerdos", label: "Obra Social Acuerdos" },
  { campo: "aporteSindical", label: "Aporte Sindical" },
  { campo: "servicioDeSepelio", label: "Servicio de Sepelio" },
];

const MESES = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];

function periodoSugerido(fechaISO: string): string {
  if (!fechaISO) return "";
  const [anio, mes] = fechaISO.split("-").map(Number);
  if (!anio || !mes) return "";
  return `${MESES[mes - 1]} ${anio}`;
}

type Conceptos = Record<string, number>;

const CONCEPTOS_VACIOS: Conceptos = Object.fromEntries(
  [...HABERES, ...DESCUENTOS].map((c) => [c.campo, 0])
);

function calcularNeto(conceptos: Conceptos): number {
  const haberes = HABERES.reduce((acc, c) => acc + (conceptos[c.campo] || 0), 0);
  const descuentos = DESCUENTOS.reduce((acc, c) => acc + (conceptos[c.campo] || 0), 0);
  return haberes - descuentos;
}

export function LiquidacionForm({
  idSalario,
  onGuardada,
  onCancelar,
}: {
  idSalario?: number | null;
  onGuardada: () => Promise<void> | void;
  onCancelar?: () => void;
}) {
  const { showToast } = useToast();
  const [empleado, setEmpleado] = useState<{ id: number | null; nombre: string | null }>({
    id: null,
    nombre: null,
  });
  const [fechaPago, setFechaPago] = useState("");
  const [periodoEditadoAMano, setPeriodoEditadoAMano] = useState(false);
  const [periodoLiquidado, setPeriodoLiquidado] = useState("");
  const [conceptos, setConceptos] = useState<Conceptos>(CONCEPTOS_VACIOS);
  const [archivo, setArchivo] = useState<File | null>(null);
  const [duplicadoAviso, setDuplicadoAviso] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Cargar datos si estamos en modo edición
  const { data: detalle, isLoading: cargandoDetalle } = useQuery({
    queryKey: ["liquidacion-detalle", idSalario],
    queryFn: () => fetchLiquidacion(idSalario!),
    enabled: !!idSalario,
  });

  useEffect(() => {
    if (detalle) {
      setEmpleado({ id: detalle.idContacto, nombre: detalle.empleado });
      setFechaPago(detalle.fechaPago || "");
      setPeriodoLiquidado(detalle.periodoLiquidado || "");
      setPeriodoEditadoAMano(true);
      const nuevosConceptos: Conceptos = {};
      [...HABERES, ...DESCUENTOS].forEach((c) => {
        nuevosConceptos[c.campo] = (detalle as any)[c.campo] ?? 0;
      });
      setConceptos(nuevosConceptos);
    }
  }, [detalle]);

  function actualizarFecha(valor: string) {
    setFechaPago(valor);
    if (!periodoEditadoAMano && !idSalario) {
      setPeriodoLiquidado(periodoSugerido(valor));
    }
  }

  function actualizarConcepto(campo: string, valor: number) {
    setConceptos((prev) => ({ ...prev, [campo]: valor }));
  }

  async function guardar(confirmarDuplicado: boolean) {
    if (!empleado.id) {
      setError("Elegí un empleado.");
      return;
    }
    if (!fechaPago) {
      setError("Ingresá la fecha de pago.");
      return;
    }
    if (!periodoLiquidado.trim()) {
      setError("Ingresá el período liquidado.");
      return;
    }

    setError(null);
    setGuardando(true);
    try {
      const request: NuevaLiquidacionRequest = {
        idContacto: empleado.id,
        fechaPago,
        periodoLiquidado: periodoLiquidado.trim(),
        confirmarDuplicado,
        ...conceptos,
      };

      let idFinal = idSalario;
      if (idSalario) {
        await actualizarLiquidacion(idSalario, request);
        showToast("Liquidación actualizada con éxito.", "success");
      } else {
        const resultado = await crearLiquidacion(request);
        idFinal = resultado.idSalario;
        showToast("Liquidación guardada.", "success");
      }

      setDuplicadoAviso(null);

      if (archivo && idFinal) {
        try {
          await subirRecibo(idFinal, archivo);
          showToast("Recibo subido.", "success");
        } catch (e) {
          showToast(
            e instanceof ApiError
              ? `Liquidación guardada, pero falló el recibo: ${e.message}`
              : "Liquidación guardada, pero falló la subida del recibo.",
            "danger"
          );
        }
      }

      await onGuardada();
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setDuplicadoAviso(e.message);
      } else {
        setError(e instanceof ApiError ? e.message : "Error al guardar la liquidación.");
      }
    } finally {
      setGuardando(false);
    }
  }

  const neto = calcularNeto(conceptos);
  const esSierra = empleado.id === 374;

  if (idSalario && cargandoDetalle) {
    return (
      <div className="rounded-md border border-border bg-surface-sunken p-6 text-center text-sm">
        Cargando datos de la liquidación…
      </div>
    );
  }

  return (
    <div className="space-y-4 rounded-md border border-border bg-surface-sunken p-5 shadow-sm">
      <div className="flex items-center justify-between border-b border-border pb-3">
        <h2 className="text-base font-semibold text-ink">
          {idSalario ? `Edición de liquidación · ${periodoLiquidado || ""}` : "Nueva liquidación"}
        </h2>
        {onCancelar && (
          <button
            type="button"
            onClick={onCancelar}
            className="text-xs text-ink-secondary hover:text-ink underline"
          >
            Cerrar formulario
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div>
          {idSalario ? (
            <label className="text-sm">
              Empleado
              <input
                className={filterInputClass}
                disabled
                value={empleado.nombre ?? ""}
              />
            </label>
          ) : (
            <ContactoSelect
              label="Empleado"
              tipoContacto="Empleado"
              value={empleado.id}
              razonSocial={empleado.nombre}
              onChange={(id, nombre) => setEmpleado({ id, nombre })}
              placeholder="Buscar empleado…"
            />
          )}
        </div>
        <label className="text-sm">
          Fecha de pago
          <input
            type="date"
            className={filterInputClass}
            value={fechaPago}
            onChange={(e) => actualizarFecha(e.target.value)}
          />
        </label>
        <label className="text-sm">
          Período liquidado
          <input
            className={filterInputClass}
            value={periodoLiquidado}
            onChange={(e) => {
              setPeriodoEditadoAMano(true);
              setPeriodoLiquidado(e.target.value);
            }}
            placeholder="Ej: Octubre 2026"
          />
        </label>
      </div>

      {/* Recuadro especial para Adicional de Marcelo Sierra y Asiento de Caja */}
      {idSalario && esSierra && (
        <div className="rounded border border-finance/30 bg-blue-50/50 p-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h3 className="text-sm font-semibold text-finance">
                Adicional fuera de recibo (Marcelo Sierra)
              </h3>
              <p className="text-xs text-ink-secondary mt-0.5">
                Cálculo del 30% + feriados 8,5% y asiento de egreso en efectivo de la Caja Giamigli SA.
              </p>
            </div>
            <div>
              <AdicionalSierra idSalario={idSalario} fechaSugerida={fechaPago} />
            </div>
          </div>
        </div>
      )}

      <div>
        <h3 className="text-sm font-medium text-ink-secondary">
          Haberes <span className="font-normal">(siempre en positivo, como en el recibo)</span>
        </h3>
        <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {HABERES.map((c) => (
            <label key={c.campo} className="text-sm">
              {c.label}
              <MoneyInput
                className={filterInputClass}
                moneda="Pesos"
                value={conceptos[c.campo] || 0}
                onChange={(v) => actualizarConcepto(c.campo, v)}
              />
            </label>
          ))}
        </div>
      </div>

      <div>
        <h3 className="text-sm font-medium text-ink-secondary">
          Descuentos <span className="font-normal">(siempre en positivo — se restan solos)</span>
        </h3>
        <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {DESCUENTOS.map((c) => (
            <label key={c.campo} className="text-sm">
              {c.label}
              <MoneyInput
                className={filterInputClass}
                moneda="Pesos"
                value={conceptos[c.campo] || 0}
                onChange={(v) => actualizarConcepto(c.campo, v)}
              />
            </label>
          ))}
        </div>
      </div>

      <label className="block text-sm">
        Adjuntar / Reemplazar recibo (PDF)
        <input
          type="file"
          accept="application/pdf"
          className={filterInputClass}
          onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
        />
      </label>

      <div className="flex items-center justify-between rounded-md border border-border bg-surface px-4 py-3">
        <span className="text-sm font-medium text-ink-secondary">Neto total liquidado</span>
        <span className="text-xl font-bold text-ink">{formatMoneda(neto)}</span>
      </div>

      {error && <p className="text-sm text-status-danger">{error}</p>}

      {duplicadoAviso && (
        <div className="space-y-2 rounded-md border border-status-danger bg-status-danger-bg px-4 py-3 text-sm text-status-danger">
          <p>{duplicadoAviso}</p>
          <button
            type="button"
            disabled={guardando}
            onClick={() => guardar(true)}
            className="rounded border border-status-danger px-3 py-1 text-xs hover:bg-status-danger hover:text-white"
          >
            Guardar de todos modos
          </button>
        </div>
      )}

      <div className="flex justify-end gap-3 pt-2">
        {onCancelar && (
          <button
            type="button"
            disabled={guardando}
            onClick={onCancelar}
            className="rounded border border-border px-4 py-2 text-sm text-ink hover:bg-surface"
          >
            Cancelar
          </button>
        )}
        <button
          type="button"
          disabled={guardando}
          onClick={() => guardar(false)}
          className="rounded bg-finance px-5 py-2 text-sm font-medium text-white hover:bg-finance/90 disabled:opacity-50"
        >
          {guardando ? "Guardando…" : idSalario ? "Guardar cambios" : "Guardar liquidación"}
        </button>
      </div>
    </div>
  );
}

// Mantener compatibilidad retroactiva con imports de NuevaLiquidacionForm
export const NuevaLiquidacionForm = LiquidacionForm;
