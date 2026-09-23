"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/components/auth/AuthContext";

/** Redirige a `/login` sin sesión válida (FR-010). Mientras `fetchMe()`
 * está en curso no renderiza contenido protegido, para no mostrar datos
 * de `WC` por un instante antes de saber si hay sesión. */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { usuario, isLoading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const esLogin = pathname === "/login";

  useEffect(() => {
    if (!isLoading && !usuario && !esLogin) {
      router.replace("/login");
    }
  }, [isLoading, usuario, esLogin, router]);

  if (esLogin) return <>{children}</>;

  if (isLoading || !usuario) return null;

  return <>{children}</>;
}
