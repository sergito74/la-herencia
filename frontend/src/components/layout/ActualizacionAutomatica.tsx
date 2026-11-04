"use client";

import { useQueryClient } from "@tanstack/react-query";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { API_BASE_URL } from "@/services/apiClient";

const INTERVALO_MS = 10_000;

interface Version {
  inicio: string;
  build: string | null;
  ultimaEscritura: string | null;
}

/**
 * La pantalla se mantiene al día sola (04/11/2026), sin depender de recargar a mano:
 * - Si cambió algún dato en la base (desde esta pestaña, otra, la rutina, una carga o un script), vuelve a pedir lo
 *   que se está mostrando. No toca lo que se esté escribiendo en un formulario.
 * - Si el sistema se actualizó (pantalla nueva), se recarga al cambiar de página o de pestaña, para no perder una
 *   carga a medio hacer; mientras tanto avisa con un botón para hacerlo ya.
 */
export function ActualizacionAutomatica() {
  const qc = useQueryClient();
  const pathname = usePathname();
  const base = useRef<Version | null>(null);
  const [versionNueva, setVersionNueva] = useState(false);
  const pendiente = useRef(false);

  useEffect(() => {
    let vivo = true;
    const revisar = async () => {
      let v: Version;
      try {
        const r = await fetch(`${API_BASE_URL}/api/sesion/version`, { cache: "no-store" });
        if (!r.ok) return;
        v = await r.json();
      } catch {
        return; // backend reiniciándose: se reintenta en la próxima vuelta
      }
      if (!vivo) return;
      const antes = base.current;
      if (!antes) {
        base.current = v;
        return;
      }
      if (v.build && antes.build && v.build !== antes.build) {
        pendiente.current = true;
        setVersionNueva(true);
        if (document.hidden) window.location.reload();
        return;
      }
      if (v.ultimaEscritura !== antes.ultimaEscritura || v.inicio !== antes.inicio) {
        base.current = v;
        qc.invalidateQueries({ predicate: (q) => q.queryKey[0] !== "auth", refetchType: "active" });
      }
    };
    revisar();
    const t = window.setInterval(revisar, INTERVALO_MS);
    const alVolver = () => {
      if (document.hidden && pendiente.current) window.location.reload();
      else if (!document.hidden) revisar();
    };
    document.addEventListener("visibilitychange", alVolver);
    return () => {
      vivo = false;
      window.clearInterval(t);
      document.removeEventListener("visibilitychange", alVolver);
    };
  }, [qc]);

  // Al pasar a otra página con una versión nueva pendiente: se recarga ahí (no hay nada a medio cargar).
  useEffect(() => {
    if (pendiente.current) window.location.reload();
  }, [pathname]);

  if (!versionNueva) return null;
  return (
    <div className="fixed bottom-4 right-4 z-50 flex items-center gap-3 rounded-md border border-finance bg-surface px-4 py-2 text-sm shadow-lg">
      <span>El sistema se actualizó.</span>
      <button type="button" onClick={() => window.location.reload()} className="rounded bg-finance px-3 py-1 text-white">
        Actualizar ahora
      </button>
    </div>
  );
}
