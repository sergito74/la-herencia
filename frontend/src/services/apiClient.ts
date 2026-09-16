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

/** GET-only JSON fetch helper. No write verbs are exposed by this client. */
export async function apiGet<T>(
  path: string,
  params?: Record<string, string | number | undefined>
): Promise<T> {
  const url = new URL(path, API_BASE_URL);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }

  const response = await fetch(url.toString(), { method: "GET" });

  if (!response.ok) {
    const detail = await response.text().catch(() => "");
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
    const detail = await response.text().catch(() => "");
    throw new ApiError(response.status, detail || response.statusText);
  }

  return (await response.json()) as T;
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
