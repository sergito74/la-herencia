"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/components/auth/AuthContext";
import { login } from "@/services/authApi";
import { ApiError } from "@/services/apiClient";

export default function LoginPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { usuario, isLoading } = useAuth();
  const [nombreUsuario, setNombreUsuario] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    if (!isLoading && usuario) {
      router.replace("/");
    }
  }, [isLoading, usuario, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      const usuarioLogueado = await login(nombreUsuario, password);
      queryClient.setQueryData(["auth", "me"], usuarioLogueado);
      router.replace("/");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Usuario o contraseña incorrectos");
      } else {
        setError("No se pudo iniciar sesión. Intentá de nuevo.");
      }
    } finally {
      setEnviando(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-lg border border-border bg-surface p-8 shadow-sm"
      >
        <div className="mb-6 flex items-center gap-2 text-ink-primary">
          <span className="flex h-8 w-8 items-center justify-center rounded-md bg-agro text-sm text-white">
            LH
          </span>
          <span className="text-lg font-semibold">La Herencia</span>
        </div>

        <label className="mb-1 block text-sm font-medium text-ink-secondary" htmlFor="usuario">
          Usuario
        </label>
        <input
          id="usuario"
          type="text"
          autoComplete="username"
          required
          value={nombreUsuario}
          onChange={(e) => setNombreUsuario(e.target.value)}
          className="mb-4 w-full rounded-sm border border-border px-3 py-2 text-sm text-ink-primary"
        />

        <label className="mb-1 block text-sm font-medium text-ink-secondary" htmlFor="password">
          Contraseña
        </label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mb-4 w-full rounded-sm border border-border px-3 py-2 text-sm text-ink-primary"
        />

        {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={enviando}
          className="w-full rounded-md bg-agro px-3 py-2 text-sm font-medium text-white disabled:opacity-60"
        >
          {enviando ? "Ingresando..." : "Ingresar"}
        </button>
      </form>
    </main>
  );
}
