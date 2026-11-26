"use client";

import { useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { SideDrawer } from "@/components/ui/SideDrawer";

/** Marca "Revisado y aceptado" con motivo obligatorio (queda registrado con usuario y fecha; se puede quitar). */
export function MarcaRevisado({ onAceptar, titulo = "Revisado y aceptado", detalle }: {
  onAceptar: (motivo: string) => Promise<unknown>;
  titulo?: string;
  detalle?: string;
}) {
  const [abierto, setAbierto] = useState(false);
  const [motivo, setMotivo] = useState("");
  const [pendiente, setPendiente] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const confirmar = async () => {
    setPendiente(true);
    setError(null);
    try {
      await onAceptar(motivo.trim());
      setAbierto(false);
      setMotivo("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo registrar.");
    } finally {
      setPendiente(false);
    }
  };
  return (
    <SoloLectura>
      <button type="button" className="text-xs text-ink-secondary underline"
        title="Queda registrado con tu usuario, la fecha y el motivo; se puede quitar después" onClick={() => setAbierto(true)}>
        {titulo}
      </button>
      {abierto && (
        <SideDrawer open onClose={() => setAbierto(false)} title={titulo}>
          {detalle && <p className="mb-3 text-sm text-ink-secondary">{detalle}</p>}
          <label className="block text-sm">¿Por qué se acepta así?
            <textarea value={motivo} onChange={(e) => setMotivo(e.target.value)} rows={3}
              className="w-full rounded-md border border-border bg-surface px-2 py-1 text-sm" />
          </label>
          {error && <p className="mt-2 text-sm text-status-danger">{error}</p>}
          <button type="button" disabled={motivo.trim().length < 3 || pendiente} onClick={confirmar}
            className="mt-3 rounded-md bg-finance px-3 py-1.5 text-sm text-white disabled:opacity-50">Aceptar</button>
        </SideDrawer>
      )}
    </SoloLectura>
  );
}
