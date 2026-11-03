"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { formatFechaHora } from "@/lib/format";
import { ejecutarRutina, getEstadoRutina } from "@/services/documentosNuevosApi";

const ESTADO: Record<string, string> = {
  en_curso: "En curso",
  ok: "Terminó bien",
  con_problemas: "Terminó con cuentas a revisar",
  incompleta: "Se cortó antes de terminar",
};

/** Rutina diaria de documentos nuevos (043, FR-013): corre sola a las 7:00 y a las 14:00; también se puede pedir a mano. */
import { AvisoFacturasAtrasadas } from "@/components/facturas-faltantes/AvisoFacturasAtrasadas";

export function RutinaPanel() {
  const q = useQuery({ queryKey: ["documentos-nuevos", "rutina"], queryFn: getEstadoRutina, refetchInterval: 15 * 1000 });
  const qc = useQueryClient();
  const [pedida, setPedida] = useState(false);
  const ejecutar = useMutation({
    mutationFn: ejecutarRutina,
    onSuccess: () => { setPedida(true); qc.invalidateQueries({ queryKey: ["documentos-nuevos"] }); },
  });
  if (!q.data) return null;
  const u = q.data.ultima;
  const enCurso = u?.estado === "en_curso";

  return (
    <>
    <AvisoFacturasAtrasadas />
    <section className="rounded-md border border-border bg-surface px-3 py-2 text-sm">
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-semibold">Rutina diaria (7:00 y 14:00)</h2>
        <SoloLectura>
          <button type="button" disabled={enCurso || ejecutar.isPending} onClick={() => ejecutar.mutate()}
            className="rounded-md border border-border px-3 py-1 text-xs font-medium disabled:opacity-50">
            {enCurso ? "Buscando..." : "Buscar ahora"}
          </button>
        </SoloLectura>
      </div>
      {pedida && !enCurso && <p className="text-ink-secondary">Pedido recibido: arranca en menos de un minuto.</p>}
      {ejecutar.isError && <p className="text-amber-900">No se pudo iniciar. Puede que ya esté corriendo.</p>}
      <p className="text-ink-secondary">
        Trae lo nuevo de las cuentas y de los mails, y lo deja para revisar en el menú de cada módulo.
        {q.data.proxima && <> Próxima: <strong>{formatFechaHora(q.data.proxima)}</strong>.</>}
      </p>
      {u ? (
        <p className="mt-1 text-ink-secondary">
          Última: {formatFechaHora(u.inicio)} · {ESTADO[u.estado] ?? u.estado} · {u.cuentasCorridas} cuentas
          {u.cuentasConProblemas ? ` (${u.cuentasConProblemas} con problemas)` : ""} · {u.mailsLeidos} mails ·{" "}
          {u.documentosNuevos} documentos nuevos ({u.cargadosSolos} cargados solos, {u.paraCargarAMano} para cargar a mano)
          {u.mensaje && <span className="block text-amber-900">{u.mensaje}</span>}
        </p>
      ) : (
        <p className="mt-1 text-ink-muted">Todavía no corrió.</p>
      )}
    </section>
    </>
  );
}
