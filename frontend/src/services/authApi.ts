"use client";

import { API_BASE_URL, ApiError } from "./apiClient";

export interface Usuario {
  idUsuario: number;
  usuario: string;
  nombre: string | null;
  rol: "Administrador" | "Lectura";
}

async function leerDetalle(response: Response): Promise<string> {
  const texto = await response.text().catch(() => "");
  try {
    const parsed = JSON.parse(texto);
    if (typeof parsed?.detail === "string") return parsed.detail;
  } catch {
    // texto crudo
  }
  return texto;
}

export async function login(usuario: string, password: string): Promise<Usuario> {
  const response = await fetch(new URL("/api/auth/login", API_BASE_URL), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ usuario, password }),
    credentials: "include",
  });

  if (!response.ok) {
    const detail = await leerDetalle(response);
    throw new ApiError(response.status, detail || response.statusText);
  }

  return (await response.json()) as Usuario;
}

export async function logout(): Promise<void> {
  await fetch(new URL("/api/auth/logout", API_BASE_URL), {
    method: "POST",
    credentials: "include",
  });
}

export async function fetchMe(): Promise<Usuario | null> {
  const response = await fetch(new URL("/api/auth/me", API_BASE_URL), {
    method: "GET",
    credentials: "include",
  });

  if (response.status === 401) return null;

  if (!response.ok) {
    const detail = await leerDetalle(response);
    throw new ApiError(response.status, detail || response.statusText);
  }

  return (await response.json()) as Usuario;
}
