"use client";

import { useState } from "react";

import { ApiError } from "@/services/apiClient";
import { crearTipoLabor, type TipoLabor } from "@/services/ordenesApi";
import { useToast } from "@/components/ui/Toast";

/** Alta de un nuevo Tipo de Labor (Historia 7): catálogo administrable, no
 * hardcodeado en el código (FR-010). */
export function TipoLaborAdmin({ tiposLabor, onCreado }: { tiposLabor: TipoLabor[]; onCreado: () => void }) {
  const { showToast } = useToast();
  const [nombre, setNombre] = useState("");
  const [guardando, setGuardando] = useState(false);

  async function agregar() {
    if (!nombre.trim()) return;
    setGuardando(true);
    try {
      await crearTipoLabor(nombre.trim());
      showToast("Tipo de labor agregado.", "success");
      setNombre("");
      onCreado();
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "No se pudo agregar el tipo de labor.", "danger");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div className="rounded border border-border p-4">
      <h2 className="mb-2 text-lg font-medium">Tipos de labor</h2>
      <ul className="mb-3 list-disc pl-5 text-sm">
        {tiposLabor.map((t) => (
          <li key={t.idTipoLabor}>{t.nombre}</li>
        ))}
      </ul>
      <div className="flex items-end gap-2">
        <label className="text-sm">
          Nuevo tipo de labor
          <input className="mt-1 block rounded border border-border px-2 py-1.5" value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="ej. Cosecha" />
        </label>
        <button type="button" onClick={agregar} disabled={guardando || !nombre.trim()} className="rounded bg-finance px-3 py-1.5 text-sm text-white disabled:opacity-50">
          Agregar
        </button>
      </div>
    </div>
  );
}
