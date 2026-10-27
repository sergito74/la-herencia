"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { formatFecha } from "@/lib/format";
import { autorizar, revocarAutorizacion, type Portal } from "@/services/bovedaApi";

function hoy(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Autorización del portal (042, US4, T020). Sin autorización vigente el
 * sistema no entra al portal, aunque tenga credenciales. */
export function AutorizacionPanel({ portal }: { portal: Portal }) {
  const qc = useQueryClient();
  const [fecha, setFecha] = useState(hoy());
  const [por, setPor] = useState("Sergio");
  const [fuente, setFuente] = useState("");
  const [abierto, setAbierto] = useState(false);
  const refrescar = () => qc.invalidateQueries({ queryKey: ["boveda"] });
  const alta = useMutation({
    mutationFn: () => autorizar(portal.idPortal, { fecha, autorizadoPor: por.trim(), fuente: fuente.trim() || null }),
    onSuccess: () => { setAbierto(false); refrescar(); },
  });
  const baja = useMutation({ mutationFn: () => revocarAutorizacion(portal.idPortal), onSuccess: refrescar });
  const a = portal.autorizacion;

  return (
    <div className="space-y-2 text-sm">
      {a.vigente ? (
        <p>
          Autorizado por <strong>{a.autorizadoPor}</strong> el {formatFecha(a.fecha)} — solo consulta y descarga.
          {a.fuente && <span className="text-ink-secondary"> Fuente: {a.fuente}</span>}
        </p>
      ) : (
        <p className="text-red-700">Sin autorización: el sistema no entra a este portal.</p>
      )}
      {abierto ? (
        <form className="flex flex-wrap items-end gap-2" onSubmit={(e) => { e.preventDefault(); alta.mutate(); }}>
          <label className="text-xs">Fecha<input type="date" required value={fecha} onChange={(e) => setFecha(e.target.value)}
            className="block rounded-md border border-border px-2 py-1 text-sm" /></label>
          <label className="text-xs">Autorizó<input required maxLength={60} value={por} onChange={(e) => setPor(e.target.value)}
            className="block rounded-md border border-border px-2 py-1 text-sm" /></label>
          <label className="flex-1 text-xs">Fuente (opcional)<input maxLength={300} value={fuente} onChange={(e) => setFuente(e.target.value)}
            className="block w-full rounded-md border border-border px-2 py-1 text-sm" /></label>
          <button type="submit" disabled={alta.isPending} className="rounded-md bg-finance px-3 py-1 text-xs font-medium text-white">Registrar</button>
          <button type="button" className="text-xs underline" onClick={() => setAbierto(false)}>Cancelar</button>
          {alta.isError && <span className="text-xs text-red-700">{alta.error.message}</span>}
        </form>
      ) : (
        <div className="flex gap-3">
          <button type="button" className="text-xs text-finance underline" onClick={() => setAbierto(true)}>
            {a.vigente ? "Registrar nueva autorización" : "Autorizar"}
          </button>
          {a.vigente && (
            <button type="button" disabled={baja.isPending} className="text-xs text-red-700 underline"
              onClick={() => { if (confirm("¿Revocar la autorización? El sistema dejará de entrar a este portal.")) baja.mutate(); }}>
              Revocar
            </button>
          )}
        </div>
      )}
    </div>
  );
}
