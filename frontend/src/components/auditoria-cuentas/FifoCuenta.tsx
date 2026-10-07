"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { formatMoneda } from "@/lib/format";
import { aplicarFifo, revertirFifo, simularFifo, type ResultadoFifo } from "@/services/auditoriaCuentasApi";

/** Recalcula qué pago cubre qué factura en esta cuenta (FIFO): primero se ve cómo quedaría, después se aplica, y se puede deshacer. El saldo no cambia. */
export function FifoCuenta({ idContacto }: { idContacto: number }) {
  const qc = useQueryClient();
  const [resultado, setResultado] = useState<ResultadoFifo | null>(null);
  const [aplicada, setAplicada] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const refrescar = () => {
    for (const k of ["auditoria-revision", "auditoria-hallazgos", "auditoria-resumen", "auditoria-grupo"]) qc.invalidateQueries({ queryKey: [k] });
  };
  const fallo = (e: unknown) => setError(e instanceof Error ? e.message : "No se pudo completar.");
  const simular = useMutation({
    mutationFn: () => simularFifo(idContacto),
    onSuccess: (r) => { setResultado(r); setAplicada(false); setError(null); },
    onError: fallo,
  });
  const aplicar = useMutation({
    mutationFn: () => aplicarFifo(idContacto, resultado!.idEjecucion),
    onSuccess: () => { setAplicada(true); setError(null); refrescar(); },
    onError: fallo,
  });
  const deshacer = useMutation({
    mutationFn: () => revertirFifo(idContacto, resultado!.idEjecucion),
    onSuccess: () => { setAplicada(false); setResultado(null); setError(null); refrescar(); },
    onError: fallo,
  });
  const c = resultado?.contacto;

  return (
    <SoloLectura>
      <section className="rounded border border-line p-3 text-xs">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-sm font-semibold">Imputaciones de los pagos</h2>
          <button type="button" disabled={simular.isPending} onClick={() => simular.mutate()} className="rounded border border-line px-2 py-0.5">
            {simular.isPending ? "Calculando…" : "Ver cómo quedarían (FIFO)"}
          </button>
        </div>
        <p className="text-ink-secondary">Recalcula qué pago cubre cada factura, de la más vieja a la más nueva. No cambia el saldo de la cuenta.</p>
        {error && <p role="alert" className="mt-1 text-status-danger">{error}</p>}
        {c && resultado && (
          <div className="mt-2 space-y-1">
            <p>
              Facturado <b>{formatMoneda(c.facturadoAntes)}</b> · Pagado <b>{formatMoneda(c.pagadoAntes)}</b>
            </p>
            <p>
              Imputado hoy: <b>{formatMoneda(c.aplicadoAntes)}</b> {c.cerrabaAntes ? "(las facturas cierran)" : `(faltan imputar ${formatMoneda(c.facturadoAntes - c.aplicadoAntes)})`}
            </p>
            <p>
              Con FIFO: <b>{formatMoneda(c.aplicadoDespues)}</b> {c.cierraDespues ? "(todas las facturas cierran)" : "(no llega a cerrar: queda para revisar)"}
              {c.anticipoAbierto > 0.005 && <> · pagado de más (anticipo): {formatMoneda(c.anticipoAbierto)}</>}
            </p>
            {c.marcas.map((m) => <p key={m.codigo} className="text-ink-secondary">• {m.descripcion}</p>)}
            <p className="text-ink-secondary">{resultado.aplicaciones} imputaciones nuevas en lugar de {resultado.aplicacionesVigentes} actuales.</p>
            {c.tendencia === "empeora" ? (
              <p className="text-status-danger">Este recálculo deja la cuenta peor que ahora: no se puede aplicar desde acá.</p>
            ) : aplicada ? (
              <p className="text-status-success">
                Aplicado. <button type="button" disabled={deshacer.isPending} onClick={() => deshacer.mutate()} className="ml-2 rounded border border-line px-2 py-0.5">Deshacer</button>
              </p>
            ) : (
              <button type="button" disabled={aplicar.isPending} onClick={() => aplicar.mutate()} className="rounded bg-finance px-3 py-1 text-white">
                Aplicar estas imputaciones
              </button>
            )}
          </div>
        )}
      </section>
    </SoloLectura>
  );
}
