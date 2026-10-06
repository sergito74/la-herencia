"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { MoneyInput } from "@/components/ui/MoneyInput";
import { formatFecha, formatMoneda } from "@/lib/format";
import {
  anularImputaciones,
  cargarNotaAjuste,
  fetchCorrecciones,
  fetchHallazgos,
  revertirCorreccion,
  type Hallazgo,
} from "@/services/auditoriaCuentasApi";

function useRefrescarCuenta(idContacto: number) {
  const qc = useQueryClient();
  return () => {
    for (const k of ["auditoria-revision", "auditoria-movimientos", "auditoria-resumen", "auditoria-grupo", "auditoria-hallazgos", "auditoria-correcciones"])
      qc.invalidateQueries({ queryKey: [k] });
    qc.invalidateQueries({ queryKey: ["auditoria-revision", idContacto] });
  };
}

/** Pagos mal aplicados: se pueden anular (sin borrar nada, el saldo no cambia y se puede deshacer). */
export function ImputacionesSospechosas({ idContacto }: { idContacto: number }) {
  const refrescar = useRefrescarCuenta(idContacto);
  const [elegido, setElegido] = useState<Hallazgo | null>(null);
  const [motivo, setMotivo] = useState("");
  const [error, setError] = useState<string | null>(null);
  const { data } = useQuery({ queryKey: ["auditoria-hallazgos", idContacto], queryFn: () => fetchHallazgos(idContacto) });
  const anular = useMutation({
    mutationFn: () => anularImputaciones(idContacto, elegido?.idsAplicacion ?? [], motivo),
    onSuccess: () => {
      setElegido(null);
      setMotivo("");
      setError(null);
      refrescar();
    },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : "No se pudo anular."),
  });
  const lista = (data?.hallazgos ?? []).filter((h) => (h.idsAplicacion?.length ?? 0) > 0);
  if (lista.length === 0) return null;

  return (
    <section className="rounded border border-line p-3 text-xs">
      <h2 className="text-sm font-semibold">Pagos que parecen mal aplicados</h2>
      <p className="text-ink-secondary">Anular una imputación no borra nada ni cambia el saldo: solo deja de contar ese pago como aplicado a esas facturas. Se puede deshacer.</p>
      <ul className="mt-1 divide-y divide-line">
        {lista.map((h, i) => (
          <li key={i} className="flex flex-wrap items-center gap-2 py-1">
            <span>
              {h.motivo}
              {h.importe != null && <b className="ml-1">{formatMoneda(h.importe)}</b>}
              {h.cantidadFacturas != null && ` · ${h.cantidadFacturas} facturas${h.facturaMasVieja ? `, la más vieja del ${formatFecha(h.facturaMasVieja)}` : ""}`}
              {h.medio && ` · ${h.medio} ${h.idMovimiento}`}
            </span>
            <SoloLectura>
              <button type="button" onClick={() => setElegido(h)} className="rounded border border-line px-2 py-0.5">Anular estas imputaciones</button>
            </SoloLectura>
          </li>
        ))}
      </ul>
      {elegido && (
        <div role="dialog" aria-modal className="mt-2 rounded border border-finance bg-surface p-3">
          <p className="font-medium">
            ¿Anular {elegido.idsAplicacion?.length} imputaciones por {formatMoneda(elegido.importe ?? 0)}?
          </p>
          <input value={motivo} onChange={(e) => setMotivo(e.target.value)} placeholder="Motivo (obligatorio)" aria-label="Motivo" className="mt-1 w-80 rounded border border-line px-2 py-1" />
          {error && <p role="alert" className="mt-1 text-status-danger">{error}</p>}
          <div className="mt-2 flex gap-2">
            <button type="button" disabled={anular.isPending || !motivo.trim()} onClick={() => anular.mutate()} className="rounded bg-finance px-3 py-1 text-white">Anular</button>
            <button type="button" onClick={() => { setElegido(null); setError(null); }} className="rounded border border-line px-3 py-1">Cancelar</button>
          </div>
        </div>
      )}
    </section>
  );
}

/** Carga de una nota de ajuste (de débito o de crédito) para que la cuenta cierre. */
export function NotaDeAjuste({ idContacto, moneda }: { idContacto: number; moneda: "Pesos" | "Dolares" }) {
  const refrescar = useRefrescarCuenta(idContacto);
  const [abierto, setAbierto] = useState(false);
  const [tipo, setTipo] = useState<"debito" | "credito">("debito");
  const [fecha, setFecha] = useState(new Date().toISOString().slice(0, 10));
  const [importe, setImporte] = useState(0);
  const [cambio, setCambio] = useState(0);
  const [motivo, setMotivo] = useState("");
  const [error, setError] = useState<string | null>(null);
  const cargar = useMutation({
    mutationFn: () => cargarNotaAjuste(idContacto, { tipo, fecha, importe, moneda, tipoDeCambio: moneda === "Dolares" ? cambio || undefined : undefined, motivo }),
    onSuccess: () => {
      setAbierto(false);
      setImporte(0);
      setMotivo("");
      setError(null);
      refrescar();
    },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : "No se pudo cargar la nota."),
  });
  return (
    <SoloLectura>
      {!abierto ? (
        <button type="button" onClick={() => setAbierto(true)} className="rounded border border-line px-3 py-1 text-sm">Cargar nota de ajuste</button>
      ) : (
        <div role="dialog" aria-modal className="space-y-2 rounded border border-finance bg-surface p-3 text-xs">
          <p className="text-sm font-medium">Nota de ajuste</p>
          <p className="text-ink-secondary">Nota de débito: se le debe más a este contacto. Nota de crédito: se le debe menos. El importe incluye el IVA y queda como &quot;SIN DOCUMENTO&quot;.</p>
          <div className="flex flex-wrap items-end gap-2">
            <label className="flex flex-col">Tipo
              <select value={tipo} onChange={(e) => setTipo(e.target.value as "debito" | "credito")} className="rounded border border-line px-1 py-1">
                <option value="debito">Nota de débito</option>
                <option value="credito">Nota de crédito</option>
              </select>
            </label>
            <label className="flex flex-col">Fecha
              <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} className="rounded border border-line px-1 py-1" />
            </label>
            <label className="flex flex-col">Importe ({moneda === "Dolares" ? "us$" : "$"})
              <MoneyInput value={importe} onChange={setImporte} moneda={moneda} className="w-36 rounded border border-line px-1 py-1" />
            </label>
            {moneda === "Dolares" && (
              <label className="flex flex-col">Tipo de cambio
                <MoneyInput value={cambio} onChange={setCambio} moneda="Pesos" className="w-28 rounded border border-line px-1 py-1" />
              </label>
            )}
            <label className="flex flex-col">Motivo
              <input value={motivo} onChange={(e) => setMotivo(e.target.value)} className="w-72 rounded border border-line px-2 py-1" />
            </label>
          </div>
          {error && <p role="alert" className="text-status-danger">{error}</p>}
          <div className="flex gap-2">
            <button type="button" disabled={cargar.isPending || !importe || !motivo.trim()} onClick={() => cargar.mutate()} className="rounded bg-finance px-3 py-1 text-white">Cargar nota</button>
            <button type="button" onClick={() => { setAbierto(false); setError(null); }} className="rounded border border-line px-3 py-1">Cancelar</button>
          </div>
        </div>
      )}
    </SoloLectura>
  );
}

/** Correcciones aplicadas en esta cuenta, con la opción de deshacerlas. */
export function HistorialCorrecciones({ idContacto }: { idContacto: number }) {
  const refrescar = useRefrescarCuenta(idContacto);
  const { data } = useQuery({ queryKey: ["auditoria-correcciones", idContacto], queryFn: () => fetchCorrecciones(idContacto) });
  const revertir = useMutation({ mutationFn: (id: number) => revertirCorreccion(id), onSuccess: refrescar });
  if (!data || data.length === 0) return null;
  return (
    <section className="text-xs">
      <h2 className="text-sm font-semibold">Correcciones hechas en esta cuenta</h2>
      <ul className="divide-y divide-line">
        {data.map((c) => (
          <li key={c.idCorreccion} className="flex flex-wrap items-center gap-2 py-1">
            <span>{formatFecha(c.fecha)} · {c.usuario ?? "?"} · {c.detalle} · <b>{c.estado}</b></span>
            {c.estado === "aplicada" && (
              <SoloLectura>
                <button type="button" onClick={() => revertir.mutate(c.idCorreccion)} className="rounded border border-line px-2 py-0.5">Deshacer</button>
              </SoloLectura>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
