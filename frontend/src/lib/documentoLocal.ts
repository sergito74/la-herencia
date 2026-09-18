/**
 * Detección/limpieza de rutas de archivo local de Windows, usada por el
 * campo "Documento original" de `CompraForm.tsx`/`VentaHaciendaForm.tsx`/
 * `VentaGranosForm.tsx`.
 */

/** Windows "Copiar como ruta de acceso" envuelve el resultado entre
 * comillas dobles (ej. `"C:\...\archivo.pdf"`) — se quitan antes de
 * evaluar/usar la ruta, si no la detección de ruta local falla. */
export function limpiarRutaCopiada(valor: string): string {
  const v = valor.trim();
  return /^".*"$/.test(v) ? v.slice(1, -1) : v;
}

/** Carpeta base real donde vive el escaneo de documentos de Compras en
 * esta PC — los registros migrados desde Access (`documentoOriginal`)
 * suelen traer solo la ruta relativa a esta carpeta, nunca la ruta
 * completa (ver `normalizarDocumentoOriginal`). */
export const BASE_DOCUMENTOS_COMPRAS = "C:\\Users\\Sergio\\Dropbox\\Giamigli de Bolivar SA\\Compras\\";

/** Carpeta base real donde vive el escaneo de documentos de Ventas
 * (Hacienda y Granos) en esta PC — los registros migrados desde Access
 * traen la ruta relativa como `..\Ventas\...` (un nivel arriba de la
 * carpeta de Compras y hacia adentro de "Ventas"), nunca la ruta completa. */
export const BASE_DOCUMENTOS_VENTAS = "C:\\Users\\Sergio\\Dropbox\\Giamigli de Bolivar SA\\";

/** Los registros de Compras/Ventas migrados desde Access traen
 * `documentoOriginal` en un formato roto: ruta relativa (sin la carpeta
 * base) duplicada con "#" como separador, ej.
 * `"04 2026 - 03 2027\a.pdf#04 2026 - 03 2027\a.pdf#"` (Compras) o
 * `"..\Ventas\04 2026 - 03 2027\a.pdf#..\Ventas\...#"` (Ventas) — se toma
 * el primer segmento y, si no es ya una ruta/URL completa, se le antepone
 * `base` (la carpeta base real, distinta por módulo) para poder abrirlo. */
export function normalizarDocumentoOriginal(valor: string, base: string): string {
  let v = limpiarRutaCopiada(valor);
  const hashIdx = v.indexOf("#");
  if (hashIdx !== -1) v = v.slice(0, hashIdx);
  if (esRutaCompleta(v)) return v;
  // Solo las rutas relativas de Windows (con backslash) se completan con
  // la carpeta base — una URL sin protocolo (ej. "midominio.com/factura.pdf",
  // sin backslash) se deja intacta, la resuelve el otro branch de
  // `urlParaAbrirDocumento` anteponiéndole "https://".
  if (!v.includes("\\")) return v;
  // Ventas: la ruta ya trae el "..\" que sube un nivel desde Compras hasta
  // la carpeta raíz — se quita antes de anteponer `base` (que ya es esa raíz).
  const relativa = v.startsWith("..\\") ? v.slice(3) : v;
  return base + relativa;
}

function esRutaCompleta(valor: string): boolean {
  return (
    /^[a-zA-Z]:[\\/]/.test(valor) ||
    /^\\\\/.test(valor) ||
    /^file:\/\//i.test(valor) ||
    /^[a-z][a-z0-9+.-]*:\/\//i.test(valor)
  );
}

/** Ruta local de Windows (`C:\...`) o de red (`\\servidor\...`) — los
 * navegadores bloquean la navegación a `file://` desde una página http(s)
 * por seguridad, así que un link directo no funciona; se sirve el archivo
 * por HTTP desde el backend (`urlDocumentoLocal`) en su lugar. */
export function esRutaLocalWindows(valor: string, base: string): boolean {
  const v = normalizarDocumentoOriginal(valor, base);
  return /^[a-zA-Z]:[\\/]/.test(v) || /^\\\\/.test(v) || /^file:\/\//i.test(v);
}

/** URL final para el link "Abrir" de un documento original — ruta local
 * (servida por el backend) o URL externa tal cual (con `https://` si no
 * trae protocolo). `urlDocumentoLocal` se pasa por parámetro para evitar
 * una dependencia circular con `comprasApi.ts`. */
export function urlParaAbrirDocumento(
  valor: string,
  base: string,
  urlDocumentoLocal: (ruta: string) => string
): string {
  const v = normalizarDocumentoOriginal(valor, base);
  if (esRutaLocalWindows(v, base)) {
    return urlDocumentoLocal(v);
  }
  return /^[a-z][a-z0-9+.-]*:\/\//i.test(v) ? v : `https://${v}`;
}
