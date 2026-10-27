"use client";

import { useEffect } from "react";

/** Archivos servidos por el backend (PDF de compras, ARCA, recibos…): rutas que terminan en "documento-local",
 * "archivo" o "pdf". Cualquier enlace a uno se abre en una ventana nueva (pedido de Sergio, 27/10/2026). */
const DOCUMENTO = /\/api\/.*(documento-local|\/archivo|\/pdf)(\?|$)/;

export function DocumentosEnVentanaNueva() {
  useEffect(() => {
    function alHacerClic(e: MouseEvent) {
      const a = (e.target as Element | null)?.closest?.("a[href]") as HTMLAnchorElement | null;
      if (!a || e.defaultPrevented || e.button !== 0 || !DOCUMENTO.test(a.href)) return;
      e.preventDefault();
      window.open(a.href, "_blank", "popup,noopener,width=1100,height=900");
    }
    document.addEventListener("click", alHacerClic);
    return () => document.removeEventListener("click", alHacerClic);
  }, []);
  return null;
}
