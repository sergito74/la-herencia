"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { guardarParametros, type ParametrosAuditoria as Parametros } from "@/services/auditoriaCuentasApi";

/** Plazo máximo entre una factura y el pago que se le aplica (035, FR-005). */
export function ParametrosAuditoria({ parametros }: { parametros: Parametros }) {
  const qc = useQueryClient();
  const [plazo, setPlazo] = useState(String(parametros.plazoMaximoMeses));
  const [error, setError] = useState<string | null>(null);
  const guardar = useMutation({
    mutationFn: () => guardarParametros({ plazoMaximoMeses: Number(plazo) }),
    onSuccess: () => {
      setError(null);
      qc.invalidateQueries({ queryKey: ["auditoria-resumen"] });
      qc.invalidateQueries({ queryKey: ["auditoria-grupo"] });
    },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : "No se pudo guardar."),
  });

  return (
    <section className="text-xs">
      <h2 className="text-sm font-semibold">Plazo de los pagos</h2>
      <p className="text-ink-secondary">
        Un pago aplicado a una factura de hace más meses que este plazo se marca para revisar. Hoy: {parametros.plazoMaximoMeses} meses.
      </p>
      <SoloLectura>
        <div className="mt-1 flex items-center gap-2">
          <input
            inputMode="numeric"
            value={plazo}
            onChange={(e) => setPlazo(e.target.value.replace(/\D/g, ""))}
            aria-label="Plazo máximo en meses"
            className="w-16 rounded border border-line px-2 py-1"
          />
          <button type="button" disabled={guardar.isPending || !plazo} onClick={() => guardar.mutate()} className="rounded border border-line px-2 py-1">
            Guardar plazo
          </button>
          {error && <span role="alert" className="text-status-danger">{error}</span>}
        </div>
      </SoloLectura>
    </section>
  );
}
