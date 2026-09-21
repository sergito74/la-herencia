"use client";

import { useEffect } from "react";

import { API_BASE_URL } from "@/services/apiClient";

const INTERVALO_MS = 10_000;
const EVENTOS_ACTIVIDAD = ["pointerdown", "pointermove", "keydown", "wheel", "touchstart"];

// Un ID por carga de página, a nivel de módulo: el modo estricto de React monta
// el efecto dos veces y, con un ID por montaje, quedaría una pestaña fantasma.
let tabId: string | null = null;

/**
 * Avisa al backend que esta pestaña sigue abierta y si hubo actividad del
 * usuario. El lanzador de escritorio usa esto para apagar el sistema al
 * cerrar la última pestaña o tras 10 min sin actividad. Se manda como
 * text/plain para evitar el preflight CORS y poder usar sendBeacon al cerrar.
 */
export function SesionHeartbeat() {
  useEffect(() => {
    tabId ??= crypto.randomUUID();
    const id = tabId;
    let hubo = false;
    const marcar = () => {
      hubo = true;
    };

    const latir = () => {
      const activo = hubo;
      hubo = false;
      fetch(`${API_BASE_URL}/api/sesion/latido`, {
        method: "POST",
        headers: { "Content-Type": "text/plain" },
        body: JSON.stringify({ tabId: id, activo }),
        keepalive: true,
      }).catch(() => {});
    };

    const cerrar = () => {
      navigator.sendBeacon(
        `${API_BASE_URL}/api/sesion/cierre`,
        new Blob([JSON.stringify({ tabId: id })], { type: "text/plain" }),
      );
    };

    hubo = true;
    latir();
    const timer = setInterval(latir, INTERVALO_MS);
    EVENTOS_ACTIVIDAD.forEach((e) => window.addEventListener(e, marcar, { passive: true }));
    window.addEventListener("pagehide", cerrar);
    // Vuelta desde el caché de ida/vuelta: pagehide ya avisó el cierre.
    window.addEventListener("pageshow", latir);

    return () => {
      clearInterval(timer);
      EVENTOS_ACTIVIDAD.forEach((e) => window.removeEventListener(e, marcar));
      window.removeEventListener("pagehide", cerrar);
      window.removeEventListener("pageshow", latir);
    };
  }, []);

  return null;
}
