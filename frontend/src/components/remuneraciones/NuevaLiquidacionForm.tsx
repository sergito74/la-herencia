"use client";

import { useState } from "react";

import { crearLiquidacion, subirRecibo, type NuevaLiquidacionRequest } from "@/services/remuneracionesApi";
import { ApiError } from "@/services/apiClient";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { filterInputClass } from "@/components/ui/FilterBar";
import { MoneyInput } from "@/components/ui/MoneyInput";
import { useToast } from "@/components/ui/Toast";
import { formatMoneda } from "@/lib/format";

/** Conceptos "haber" (suman al neto) y "descuento" (restan) — misma
 * clasificación que `repository.py::_CONCEPTOS_HABERES/_DESCUENTOS`
 * (028, FR-014). Todos se cargan siempre en positivo, tal como figuran
 * en el recibo real. */
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

/**
 * Alta de liquidación de remuneraciones (028 US1/US2). Elegir empleado,
 * cargar los conceptos (siempre en positivo) y opcionalmente adjuntar el
 * PDF del recibo — datos numéricos y PDF son pasos independientes
 * (Assumptions de spec.md), ninguno bloquea al otro.
 */
export function NuevaLiquidacionForm({ onCreada }: { onCreada: () => Promise<void> | void }) {
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

  function actualizarFecha(valor: string) {
    setFechaPago(valor);
    if (!periodoEditadoAMano) setPeriodoLiquidado(periodoSugerido(valor));
  }

  function actualizarConcepto(campo: string, valor: number) {
    setConceptos((prev) => ({ ...prev, [campo]: valor }));
  }

  function limpiar() {
    setEmpleado({ id: null, nombre: null });
    setFechaPago("");
    setPeriodoLiquidado("");
    setPeriodoEditadoAMano(false);
    setConceptos(CONCEPTOS_VACIOS);
    setArchivo(null);
    setDuplicadoAviso(null);
    setError(null);
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
      const resultado = await crearLiquidacion(request);
      setDuplicadoAviso(null);

      if (archivo) {
        try {
          await subirRecibo(resultado.idSalario, archivo);
        } catch (e) {
          showToast(
            e instanceof ApiError
              ? `Liquidación guardada, pero falló el recibo: ${e.message}`
              : "Liquidación guardada, pero falló la subida del recibo.",
            "danger"
          );
        }
      }

      showToast("Liquidación guardada.", "success");
      limpiar();
      await onCreada();
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

  return (
    <div className="space-y-4 rounded-md border border-border bg-surface-sunken p-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div>
          <ContactoSelect
            label="Empleado"
            tipoContacto="Empleado"
            value={empleado.id}
            razonSocial={empleado.nombre}
            onChange={(id, nombre) => setEmpleado({ id, nombre })}
            placeholder="Buscar empleado…"
          />
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
            placeholder="Ej: Septiembre 2026"
          />
        </label>
      </div>

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
        Adjuntar recibo (PDF) — opcional, se puede subir después
        <input
          type="file"
          accept="application/pdf"
          className={filterInputClass}
          onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
        />
      </label>

      <div className="flex items-center justify-between rounded-md border border-border bg-surface px-4 py-2">
        <span className="text-sm text-ink-secondary">Importe neto</span>
        <span className="text-lg font-semibold">{formatMoneda(neto)}</span>
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

      <div className="flex justify-end">
        <button
          type="button"
          disabled={guardando}
          onClick={() => guardar(false)}
          className="rounded bg-finance px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          {guardando ? "Guardando…" : "Guardar liquidación"}
        </button>
      </div>
    </div>
  );
}
