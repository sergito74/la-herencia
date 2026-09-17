"use client";

import { useState } from "react";

import { TIPOS_CONTACTO, type Contacto, type ContactoInput, type TipoContacto } from "@/services/contactosApi";
import { filterInputClass } from "@/components/ui/FilterBar";

/**
 * Alta/edición de contacto (cliente/proveedor/comprador/consignatario/
 * empleado/institución) — módulo fundacional pedido explícitamente por el
 * usuario ("Falta el modulo de carga de contactos"). Escribe contra `WC`
 * únicamente vía `crearContacto`/`actualizarContacto` (regla de oro).
 */
export function ContactoForm({
  initial,
  onSubmit,
  onCancel,
  isSaving,
}: {
  initial?: Contacto | null;
  onSubmit: (input: ContactoInput) => void;
  onCancel: () => void;
  isSaving: boolean;
}) {
  const [razonSocial, setRazonSocial] = useState(initial?.razonSocial ?? "");
  const [tipoContacto, setTipoContacto] = useState<TipoContacto>(
    (initial?.tipoContacto as TipoContacto) ?? "Proveedor"
  );
  const [cuit, setCuit] = useState(initial?.cuit ?? "");
  const [esContratistaLabores, setEsContratistaLabores] = useState(
    initial?.esContratistaLabores ?? false
  );

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({
      razonSocial: razonSocial.trim(),
      tipoContacto,
      cuit: cuit.trim() || null,
      esContratistaLabores,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <label className="flex flex-col gap-1 text-sm text-ink-secondary">
        Razón social
        <input
          required
          className={filterInputClass}
          value={razonSocial}
          onChange={(e) => setRazonSocial(e.target.value)}
          placeholder="Nombre o razón social"
        />
      </label>

      <label className="flex flex-col gap-1 text-sm text-ink-secondary">
        Tipo de contacto
        <select
          className={filterInputClass}
          value={tipoContacto}
          onChange={(e) => setTipoContacto(e.target.value as TipoContacto)}
        >
          {TIPOS_CONTACTO.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1 text-sm text-ink-secondary">
        CUIT/CUIL
        <input
          className={filterInputClass}
          value={cuit}
          onChange={(e) => setCuit(e.target.value)}
          placeholder="20123456789"
          maxLength={11}
        />
      </label>

      <label className="flex items-center gap-2 text-sm text-ink-secondary">
        <input
          type="checkbox"
          checked={esContratistaLabores}
          onChange={(e) => setEsContratistaLabores(e.target.checked)}
        />
        Es contratista de labores
      </label>

      <div className="mt-2 flex justify-end gap-2">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-sm border border-border px-4 py-2 text-sm text-ink-secondary hover:text-ink-primary"
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={isSaving || razonSocial.trim().length === 0}
          className="rounded-sm bg-finance px-4 py-2 text-sm text-white hover:opacity-90 disabled:opacity-40"
        >
          {isSaving ? "Guardando…" : "Guardar"}
        </button>
      </div>
    </form>
  );
}
