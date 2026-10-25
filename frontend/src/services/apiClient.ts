"use client";

/**
 * Fetch wrapper for the La Herencia backend API.
 *
 * The development app uses SQL Server `WC` through the Python backend.
 * The official `LaHerencia` database is protected during development.
 * Any write guard belongs in the backend connection layer, not this client.
 */

import { QueryClient } from "@tanstack/react-query";

// Nunca "localhost" como default: en la PC de producción resolverlo agrega
// ~2s a cada request (ver launcher/LaHerencia.ps1). Si NEXT_PUBLIC_API_BASE_URL
// no está seteada o alguien la vuelve a poner en "localhost", este fallback
// evita que el sistema entero se sienta colgado.
const configurado = process.env.NEXT_PUBLIC_API_BASE_URL;
export const API_BASE_URL =
  configurado && !configurado.includes("localhost") ? configurado : "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;
  /** Detalle estructurado `{codigo, mensaje, ...}` cuando el backend lo envía (041 y siguientes). */
  detalle?: Record<string, unknown>;

  constructor(status: number, message: string, detalle?: Record<string, unknown>) {
    super(message);
    this.status = status;
    this.name = "ApiError";
    this.detalle = detalle;
  }
}

/** Detalle estructurado de un error `{"detail": {"codigo", "mensaje", ...}}`, si lo hay. */
export function detalleDeError(texto: string): Record<string, unknown> | undefined {
  try {
    const parsed = JSON.parse(texto);
    if (parsed?.detail && typeof parsed.detail === "object" && !Array.isArray(parsed.detail)) return parsed.detail;
  } catch {
    // no es JSON
  }
  return undefined;
}

/** FastAPI devuelve errores como `{"detail": "mensaje"}` — sin esto,
 * `ApiError.message` termina siendo el JSON crudo en vez del mensaje
 * legible (ej. el motivo del bloqueo por documento duplicado, 006). */
async function leerDetalleError(response: Response): Promise<string> {
  const texto = await response.text().catch(() => "");
  try {
    const parsed = JSON.parse(texto);
    if (typeof parsed?.detail === "string") return parsed.detail;
    if (typeof parsed?.detail?.mensaje === "string") return parsed.detail.mensaje;
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

/** ApiError con el mensaje legible y, si existe, el detalle estructurado del backend. */
async function errorDeRespuesta(response: Response): Promise<ApiError> {
  const texto = await response.text().catch(() => "");
  const detalle = detalleDeError(texto);
  const mensaje = await leerDetalleError(new Response(texto));
  return new ApiError(response.status, mensaje || response.statusText, detalle);
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

  const response = await fetch(url.toString(), { method: "GET", credentials: "include" });

  if (!response.ok) {
    throw await errorDeRespuesta(response);
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
    credentials: "include",
  });

  if (!response.ok) {
    throw await errorDeRespuesta(response);
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
    credentials: "include",
  });

  if (!response.ok) {
    throw await errorDeRespuesta(response);
  }

  return (await leerRespuesta(response)) as T;
}

/** POST multipart (subida de archivos), con la misma sesión y manejo de errores que `apiPost`. */
export async function apiPostForm<T>(path: string, form: FormData): Promise<T> {
  const response = await fetch(new URL(path, API_BASE_URL).toString(), { method: "POST", body: form, credentials: "include" });
  if (!response.ok) {
    throw await errorDeRespuesta(response);
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
    credentials: "include",
  });

  if (!response.ok) {
    throw await errorDeRespuesta(response);
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
    credentials: "include",
  });

  if (!response.ok) {
    throw await errorDeRespuesta(response);
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
