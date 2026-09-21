import { apiGet, apiPost } from "@/services/apiClient";

interface RutaResponse {
  ruta: string | null;
}

/** Abre el selector de archivos de Windows en esta PC (el backend corre acá).
 * Devuelve la ruta elegida, o null si el usuario cancela. */
export async function seleccionarArchivo(titulo: string, inicial?: string | null): Promise<string | null> {
  const r = await apiPost<RutaResponse>(
    "/api/documentos/seleccionar",
    { titulo, inicial: inicial || null },
    { "X-La-Herencia": "1" }
  );
  return r.ruta;
}

/** Ruta completa de un archivo arrastrado al navegador (que solo entrega
 * nombre/tamaño/fecha), buscándolo en el disco. Null si no se encuentra. */
export async function ubicarArchivo(file: File): Promise<string | null> {
  const r = await apiGet<RutaResponse>("/api/documentos/ubicar", {
    nombre: file.name,
    tamano: file.size,
    modificado: file.lastModified,
  });
  return r.ruta;
}
