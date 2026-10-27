"use client";

import { useEffect, useState } from "react";

import { revelar } from "@/services/bovedaApi";

const SEGUNDOS_VISIBLE = 30;

/** Muestra o copia un secreto de la bóveda (042, T016). El valor vive solo en
 * el estado del componente durante 30 s; no pasa por la caché de TanStack Query.
 * Cada uso queda auditado en el backend. */
export function Revelar({ idCredencial, campo, etiqueta = "contraseña" }: { idCredencial: number; campo: string; etiqueta?: string }) {
  const [valor, setValor] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  useEffect(() => {
    if (valor === null) return;
    const t = setTimeout(() => setValor(null), SEGUNDOS_VISIBLE * 1000);
    return () => clearTimeout(t);
  }, [valor]);

  useEffect(() => {
    if (!aviso) return;
    const t = setTimeout(() => setAviso(null), 4000);
    return () => clearTimeout(t);
  }, [aviso]);

  async function obtener(): Promise<string | null> {
    setOcupado(true);
    try {
      return (await revelar(idCredencial, campo)).valor;
    } catch (e) {
      setAviso(e instanceof Error ? e.message : "No se pudo obtener el valor");
      return null;
    } finally {
      setOcupado(false);
    }
  }

  async function mostrar() {
    const v = await obtener();
    if (v !== null) setValor(v);
  }

  async function copiar() {
    const v = await obtener();
    if (v === null) return;
    try {
      await navigator.clipboard.writeText(v);
      setAviso(`Se copió la ${etiqueta}`);
    } catch {
      setAviso("El navegador no permitió copiar");
    }
  }

  return (
    <span className="inline-flex items-center gap-2 text-xs">
      {valor !== null ? (
        <>
          <code className="rounded bg-surface-sunken px-1.5 py-0.5 font-mono text-ink-primary">{valor}</code>
          <button type="button" className="text-ink-secondary underline" onClick={() => setValor(null)}>
            Ocultar
          </button>
        </>
      ) : (
        <>
          <span className="font-mono text-ink-muted">••••••••</span>
          <button type="button" disabled={ocupado} className="text-finance underline disabled:opacity-50" onClick={mostrar}>
            Revelar
          </button>
          <button type="button" disabled={ocupado} className="text-finance underline disabled:opacity-50" onClick={copiar}>
            Copiar
          </button>
        </>
      )}
      {aviso && <span className="text-ink-secondary">{aviso}</span>}
    </span>
  );
}
