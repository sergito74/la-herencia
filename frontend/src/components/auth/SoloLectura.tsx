"use client";

import { useAuth } from "@/components/auth/AuthContext";

/** Oculta sus `children` si el usuario autenticado tiene rol `Lectura`
 * (FR-011) — defensa en profundidad, el backend ya rechaza con 403
 * (FR-006). Se puede envolver de forma incremental los botones de
 * escritura más visibles, no hace falta tocar cada pantalla de golpe. */
export function SoloLectura({ children }: { children: React.ReactNode }) {
  const { usuario } = useAuth();
  if (usuario?.rol === "Lectura") return null;
  return <>{children}</>;
}
