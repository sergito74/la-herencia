"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { MoneyInput } from "@/components/ui/MoneyInput";
import { editarAsiento, registrarAsiento, type MovimientoCuentaSocio } from "@/services/cuentasSociosApi";

const input = "mt-1 block w-full rounded-sm border border-border bg-surface px-3 py-2 text-sm";

/** Alta o edición de un asiento manual de la cuenta del socio (Debe / Haber), valuado en kg INMAG y US$ a la fecha. */
export function AsientoSocioForm({ idSocio, movimiento, onListo }: { idSocio: number; movimiento?: MovimientoCuentaSocio; onListo: () => void }) {
  const cache = useQueryClient();
  const [lado, setLado] = useState<"debe" | "haber">(movimiento?.tipo === "Devolucion" ? "haber" : "debe");
  const [fecha, setFecha] = useState(movimiento?.fecha.slice(0, 10) ?? new Date().toISOString().slice(0, 10));
  const [importe, setImporte] = useState(movimiento ? Math.abs(movimiento.importe) : 0);
  const [medio, setMedio] = useState(movimiento?.medio ?? "");
  const [motivo, setMotivo] = useState(movimiento?.motivo ?? "");
  const guardar = useMutation({
    mutationFn: () => {
      const body = { lado, fecha, importe, medio: medio || null, motivo };
      return movimiento ? editarAsiento(movimiento.idMovimiento, body) : registrarAsiento(idSocio, body);
    },
    onSuccess: async () => {
      await cache.invalidateQueries({ queryKey: ["cuenta-socio", idSocio] });
      await cache.invalidateQueries({ queryKey: ["cuentas-socios"] });
      onListo();
    },
  });
  return (
    <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); guardar.mutate(); }}>
      <fieldset className="flex gap-4 text-sm">
        <legend className="mb-1 text-sm">Lado</legend>
        <label className="flex items-center gap-2"><input type="radio" checked={lado === "debe"} onChange={() => setLado("debe")} /> Debe — el socio le debe a la empresa</label>
        <label className="flex items-center gap-2"><input type="radio" checked={lado === "haber"} onChange={() => setLado("haber")} /> Haber — a favor del socio</label>
      </fieldset>
      <div className="grid grid-cols-2 gap-3">
        <label className="text-sm">Fecha<input type="date" required className={input} value={fecha} onChange={(e) => setFecha(e.target.value)} /></label>
        <label className="text-sm">Importe en pesos<MoneyInput className={input} moneda="Pesos" value={importe} onChange={setImporte} /></label>
      </div>
      <label className="block text-sm">Concepto<input autoFocus required maxLength={255} className={input} value={motivo} onChange={(e) => setMotivo(e.target.value)} placeholder="Ej: ARBA – Patente camioneta" /></label>
      <label className="block text-sm">Medio (opcional)<input className={input} maxLength={100} value={medio} onChange={(e) => setMedio(e.target.value)} placeholder="Efectivo, transferencia, cheque…" /></label>
      <p className="text-xs text-ink-secondary">
        Se valúa solo: 50% US$ (dólar BNA) y 50% kg de novillo (histórico INML / INMAG) a la fecha, también antes de 2020.
        {movimiento && " Editar anula el asiento anterior y crea el corregido: los dos quedan en el historial."}
      </p>
      {guardar.error && <p role="alert" className="text-sm text-status-danger">{(guardar.error as Error).message}</p>}
      <button className="rounded-sm bg-agro px-4 py-2 text-sm text-white disabled:opacity-50" disabled={!importe || !motivo.trim() || guardar.isPending}>
        {guardar.isPending ? "Guardando…" : movimiento ? "Guardar corrección" : "Registrar asiento"}
      </button>
    </form>
  );
}
