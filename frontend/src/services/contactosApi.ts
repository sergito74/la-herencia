/**
 * Typed client for /api/contactos — master data (Compras/Ventas/Finanzas/
 * Personal usan este listado en vez de texto libre para elegir un
 * contacto). GET es de solo lectura; POST/PATCH escriben exclusivamente
 * contra `WC` (ver nota en `apiClient.ts`).
 */

import { apiGet, apiPatch, apiPost } from "@/services/apiClient";

export const TIPOS_CONTACTO = [
  "Banco",
  "Comprador",
  "Consignatario",
  "Empleado",
  "Multiple",
  "Organismo",
  "Proveedor",
  "Tarjeta de Credito",
] as const;

export type TipoContacto = (typeof TIPOS_CONTACTO)[number];

export interface Contacto {
  idContacto: number;
  razonSocial: string | null;
  tipoContacto: string | null;
  cuit: string | null;
  esContratistaLabores: boolean | null;
}

export interface ContactosListResponse {
  items: Contacto[];
  page: number;
  pageSize: number;
  total: number;
}

export function fetchContactos(params: {
  q?: string;
  /** Repetible — ej. un selector de proveedor de Compras admite varios tipos válidos. */
  tipoContacto?: string | string[];
  page?: number;
  pageSize?: number;
}): Promise<ContactosListResponse> {
  return apiGet<ContactosListResponse>("/api/contactos", { ...params });
}

export function fetchContacto(idContacto: number): Promise<Contacto> {
  return apiGet<Contacto>(`/api/contactos/${idContacto}`);
}

export interface ContactoInput {
  razonSocial: string;
  tipoContacto: TipoContacto;
  cuit?: string | null;
  esContratistaLabores?: boolean;
}

export function crearContacto(input: ContactoInput): Promise<Contacto> {
  return apiPost<Contacto>("/api/contactos", input);
}

export function actualizarContacto(
  idContacto: number,
  input: ContactoInput
): Promise<Contacto> {
  return apiPatch<Contacto>(`/api/contactos/${idContacto}`, input);
}
