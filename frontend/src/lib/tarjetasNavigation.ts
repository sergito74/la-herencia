export const RESUMENES_PATH = "/finanzas/tarjetas/resumenes";

export function retornoResumenes(value: string | null): string {
  if (!value) return RESUMENES_PATH;
  // Admitir únicamente el listado local y sus filtros.
  return value === RESUMENES_PATH || value.startsWith(`${RESUMENES_PATH}?`)
    ? value : RESUMENES_PATH;
}

export function conRetornoResumenes(path: string, retorno: string): string {
  return `${path}?${new URLSearchParams({ returnTo: retornoResumenes(retorno) })}`;
}
