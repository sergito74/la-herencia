"use client";

import { useLayoutEffect, useState, type ReactNode, type RefObject } from "react";
import { createPortal } from "react-dom";

/**
 * Panel desplegable que se dibuja sobre toda la página (portal a <body>, posición fija), anclado debajo del
 * elemento `ancla`. Así ninguna lista queda tapada por encabezados fijos de grillas, tarjetas o paneles con
 * scroll (20/11/2026). Si abajo no hay lugar, se abre hacia arriba. Sigue al ancla al hacer scroll o
 * cambiar el tamaño de la ventana.
 *
 * Los componentes cierran sus listas con un `mousedown` en `document` fuera de su contenedor: como el panel
 * ya no está dentro de ese contenedor, aquí se corta la propagación del `mousedown` para que un clic dentro
 * del panel no lo cierre.
 */
export function Flotante({
  ancla,
  abierto,
  children,
  className = "",
  alinear = "izquierda",
  anchoDelAncla = false,
  separacion = 4,
  maxAlto = 384,
}: {
  ancla: RefObject<HTMLElement | null>;
  abierto: boolean;
  children: ReactNode;
  className?: string;
  alinear?: "izquierda" | "derecha";
  /** El panel toma como mínimo el ancho del ancla (listas de un combo). */
  anchoDelAncla?: boolean;
  separacion?: number;
  /** Alto máximo en px (se achica si no hay lugar en la ventana). */
  maxAlto?: number;
}) {
  const [pos, setPos] = useState<{ top?: number; bottom?: number; left?: number; right?: number; minWidth?: number; maxHeight: number } | null>(null);

  useLayoutEffect(() => {
    if (!abierto) return;
    const calcular = () => {
      const el = ancla.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      const alto = window.innerHeight;
      const abajo = alto - r.bottom - separacion - 8;
      const arriba = r.top - separacion - 8;
      const haciaArriba = abajo < 220 && arriba > abajo;
      setPos({
        ...(haciaArriba ? { bottom: alto - r.top + separacion } : { top: r.bottom + separacion }),
        ...(alinear === "derecha" ? { right: window.innerWidth - r.right } : { left: r.left }),
        minWidth: anchoDelAncla ? r.width : undefined,
        maxHeight: Math.min(maxAlto, Math.max(haciaArriba ? arriba : abajo, 120)),
      });
    };
    calcular();
    window.addEventListener("scroll", calcular, true);
    window.addEventListener("resize", calcular);
    return () => {
      window.removeEventListener("scroll", calcular, true);
      window.removeEventListener("resize", calcular);
    };
  }, [abierto, ancla, alinear, anchoDelAncla, separacion, maxAlto]);

  if (!abierto || !pos || typeof document === "undefined") return null;
  const { maxHeight, ...lugar } = pos;
  return createPortal(
    <div
      className={className}
      style={{ position: "fixed", zIndex: 1000, ...lugar, maxHeight, overflowY: "auto" }}
      onMouseDown={(e) => e.stopPropagation()}
    >
      {children}
    </div>,
    document.body,
  );
}
