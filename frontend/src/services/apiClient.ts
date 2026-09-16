"use client";

/**
 * Read-only fetch wrapper for the La Herencia backend API.
 *
 * This module and every function built on top of it MUST only issue GET
 * requests: the compras module (and the backend behind it) is 100%
 * read-only (constitution principle II, FR-010).
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
