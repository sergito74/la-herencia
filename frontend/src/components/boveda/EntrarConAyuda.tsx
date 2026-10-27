"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { entrarConAyuda, type Portal } from "@/services/bovedaApi";

/** Abre en esta computadora una ventana de Chrome con el ingreso completado, para los portales que no
 * aceptan un navegador automático. Lo que se descargue ahí se guarda solo en Compras. */
export function EntrarConAyuda({ portal }: { portal: Portal }) {
  const qc = useQueryClient();
  const abrir = useMutation({
    mutationFn: () => entrarConAyuda(portal.idPortal),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["boveda"] }),
  });
  if (!portal.ingresoAsistido) return null;
  if (portal.asistidoAbierto || abrir.isSuccess) {
    return (
      <span className="text-xs text-ink-secondary">
        Ventana abierta: completá lo que falte, pasá la verificación si aparece y descargá las facturas; se guardan solas en Compras.
      </span>
    );
  }
  return (
    <span className="inline-flex flex-col gap-1">
      <button type="button" onClick={() => abrir.mutate()} disabled={abrir.isPending}
        className="w-fit rounded-md border border-border bg-surface px-2 py-1 text-xs font-medium hover:bg-surface-sunken disabled:opacity-50">
        {abrir.isPending ? "Abriendo…" : "Entrar con ayuda"}
      </button>
      {abrir.error && <span className="text-xs text-red-700">{abrir.error.message}</span>}
    </span>
  );
}
