"use client";

import { useQueryClient } from "@tanstack/react-query";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { API_BASE_URL } from "@/services/apiClient";

interface Version {
  inicio: string;
  build: string | null;
  ultimaEscritura: string | null;
}

/**
 * La pantalla se pone al día sola (04/11/2026), sin recargar a mano y sin consultar de fondo: se revisa solo al volver
 * a la pestaña/ventana o al cambiar de página, así nada se mueve mientras se está mirando.
 * - Si cambiaron datos por fuera de esta pantalla (la rutina, una sincronización, un cambio hecho desde Claude), vuelve
 *   a pedir lo que se muestra. No toca lo que se esté escribiendo en un formulario.
 * - Si el sistema se actualizó (pantalla nueva), se recarga al cambiar de página; si se detecta al volver a la pestaña,
 *   avisa con un botón, para no perder una carga a medio hacer.
 */
export function ActualizacionAutomatica() {
  const qc = useQueryClient();
  const pathname = usePathname();
  const base = useRef<Version | null>(null);
  const pendiente = useRef(false);
  const [versionNueva, setVersionNueva] = useState(false);

  const revisar = useCallback(async () => {
    let v: Version;
    try {
      const r = await fetch(`${API_BASE_URL}/api/sesion/version`, { cache: "no-store" });
      if (!r.ok) return;
      v = await r.json();
    } catch {
      return; // backend reiniciándose: se revisa la próxima vez
    }
    const antes = base.current;
    if (!antes) {
      base.current = v;
      return;
    }
    if (v.build && antes.build && v.build !== antes.build) {
      pendiente.current = true;
      setVersionNueva(true);
      return;
    }
    if (v.ultimaEscritura !== antes.ultimaEscritura || v.inicio !== antes.inicio) {
      base.current = v;
      qc.invalidateQueries({ predicate: (q) => q.queryKey[0] !== "auth", refetchType: "active" });
    }
  }, [qc]);

  useEffect(() => {
    const alVolver = () => {
      if (!document.hidden) revisar();
    };
    document.addEventListener("visibilitychange", alVolver);
    window.addEventListener("focus", alVolver);
    return () => {
      document.removeEventListener("visibilitychange", alVolver);
      window.removeEventListener("focus", alVolver);
    };
  }, [revisar]);

  // Al cambiar de página: con una versión nueva pendiente se recarga ahí (no hay nada a medio cargar); si no, se revisa.
  useEffect(() => {
    if (pendiente.current) window.location.reload();
    else revisar();
  }, [pathname, revisar]);

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
