"use client";

/**
 * Fetch wrapper for the La Herencia backend API.
 *
 * Most of this app is still GET-only against the original `LaHerencia`
 * database — that read path is unaffected. `apiPatch` (added 2026-09-17)
 * is the one exception: it's used only by features whose backend writes
 * exclusively to `WC` ("Working Copy"), never to `LaHerencia` — enforced
 * server-side in `backend/src/db/connection.py` (`execute_write`), not
 * by this client. Do not add new mutation helpers here without a
 * matching `WC`-only guard on the backend endpoint they call.
 */

import { QueryClient } from "@tanstack/react-query";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

/** FastAPI devuelve errores como `{"detail": "mensaje"}` — sin esto,
 * `ApiError.message` termina siendo el JSON crudo en vez del mensaje
 * legible (ej. el motivo del bloqueo por documento duplicado, 006). */
async function leerDetalleError(response: Response): Promise<string> {
  const texto = await response.text().catch(() => "");
  try {
    const parsed = JSON.parse(texto);
    if (typeof parsed?.detail === "string") return parsed.detail;
    // Errores de validación de negocio: el backend devuelve una lista de mensajes.
    if (Array.isArray(parsed?.detail)) {
      return parsed.detail
        .map((d: unknown) => (typeof d === "string" ? d : ((d as { msg?: string })?.msg ?? JSON.stringify(d))))
        .join(" ");
    }
  } catch {
    // No era JSON — se usa el texto crudo tal cual.
  }
  return texto;
}

/** Cuerpo JSON de una respuesta, o `undefined` si viene vacía (204 No Content). */
async function leerRespuesta(response: Response): Promise<unknown> {
  if (response.status === 204) return undefined;
  const texto = await response.text();
  return texto ? JSON.parse(texto) : undefined;
}

/** GET-only JSON fetch helper. No write verbs are exposed by this client. */
export async function apiGet<T>(
  path: string,
  params?: Record<string, string | number | string[] | undefined>
): Promise<T> {
  const url = new URL(path, API_BASE_URL);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (Array.isArray(value)) {
        for (const item of value) {
          url.searchParams.append(key, item);
        }
      } else if (value !== undefined && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }

  const response = await fetch(url.toString(), { method: "GET" });

  if (!response.ok) {
    const detail = await leerDetalleError(response);
    throw new ApiError(response.status, detail || response.statusText);
  }

  return (await response.json()) as T;
}

/** PATCH helper — ver nota en el encabezado del módulo (solo para `WC`). */
export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const url = new URL(path, API_BASE_URL);
  const response = await fetch(url.toString(), {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const detail = await leerDetalleError(response);
    throw new ApiError(response.status, detail || response.statusText);
  }

  return (await leerRespuesta(response)) as T;
}

/** POST helper — ver nota en el encabezado del módulo (solo para `WC`). */
export async function apiPost<T>(
  path: string,
  body: unknown,
  extraHeaders?: Record<string, string>
): Promise<T> {
  const url = new URL(path, API_BASE_URL);
  const response = await fetch(url.toString(), {
    method: "POST",
    headers: { "Content-Type": "application/json", ...extraHeaders },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const detail = await leerDetalleError(response);
    throw new ApiError(response.status, detail || response.statusText);
  }

  return (await leerRespuesta(response)) as T;
}

/** PUT helper — ver nota en el encabezado del módulo (solo para `WC`). */
export async function apiPut<T>(
  path: string,
  body: unknown,
  extraHeaders?: Record<string, string>
): Promise<T> {
  const url = new URL(path, API_BASE_URL);
  const response = await fetch(url.toString(), {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...extraHeaders },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const detail = await leerDetalleError(response);
    throw new ApiError(response.status, detail || response.statusText);
  }

  return (await leerRespuesta(response)) as T;
}

/** DELETE helper — ver nota en el encabezado del módulo (solo para `WC`). Sin body de respuesta (204).
 * `keepalive` deja la petición en curso sobrevivir a que la pestaña se
 * cierre/navegue (ej. liberar un lock de edición en `pagehide` — sin esto,
 * el cleanup normal de React puede cancelarse antes de completarse). */
export async function apiDelete(
  path: string,
  extraHeaders?: Record<string, string>,
  keepalive = false
): Promise<void> {
  const url = new URL(path, API_BASE_URL);
  const response = await fetch(url.toString(), {
    method: "DELETE",
    headers: { ...extraHeaders },
    keepalive,
  });

  if (!response.ok) {
    const detail = await leerDetalleError(response);
    throw new ApiError(response.status, detail || response.statusText);
  }
}

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        retry: 1,
      },
    },
  });
}
