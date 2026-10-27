"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Revelar } from "@/components/boveda/Revelar";
import { cambiarClave, getCredenciales, type Portal } from "@/services/bovedaApi";

/** Credencial de un portal: usuario, revelar/copiar y cambio de contraseña (042, US1). */
export function CredencialPanel({ portal }: { portal: Portal }) {
  const qc = useQueryClient();
  const credenciales = useQuery({ queryKey: ["boveda", "credenciales"], queryFn: getCredenciales });
  const [nueva, setNueva] = useState("");
  const [abierto, setAbierto] = useState(false);
  const cambio = useMutation({
    mutationFn: () => cambiarClave(portal.credencial!.idCredencial, nueva),
    onSuccess: () => {
      setNueva("");
      setAbierto(false);
      qc.invalidateQueries({ queryKey: ["boveda"] });
    },
  });

  if (!portal.credencial) {
    return <p className="text-sm text-ink-muted">Este portal no tiene credencial. Se puede asignar editando el portal.</p>;
  }
  const c = portal.credencial;
  const detalle = credenciales.data?.find((x) => x.idCredencial === c.idCredencial);
  const compartida = (detalle?.portales.length ?? 0) > 1;

  return (
    <div className="space-y-2 text-sm">
      <div className="grid grid-cols-[10rem_1fr] gap-y-1">
        <span className="text-ink-secondary">Credencial</span>
        <span>{c.nombre}{compartida && <span className="ml-2 text-xs text-ink-muted">(compartida con otros portales)</span>}</span>
        <span className="text-ink-secondary">Usuario</span>
        <span>{c.usuario ?? "—"}</span>
        <span className="text-ink-secondary">Contraseña</span>
        <span>
          {c.claveConfigurada ? <Revelar idCredencial={c.idCredencial} campo="clave" /> : <span className="text-red-700">Falta cargarla</span>}
          {c.estado === "rechazada" && <span className="ml-2 text-xs text-red-700">El portal la rechazó: actualizarla</span>}
        </span>
        {detalle?.datos.map((d) => (
          <div key={d.nombre} className="contents">
            <span className="text-ink-secondary">{d.nombre}</span>
            <span>{d.secreto ? <Revelar idCredencial={c.idCredencial} campo={`dato:${d.nombre}`} etiqueta={d.nombre} /> : d.valor}</span>
          </div>
        ))}
      </div>
      {abierto ? (
        <form className="flex items-center gap-2" autoComplete="off"
          onSubmit={(e) => { e.preventDefault(); if (nueva) cambio.mutate(); }}>
          <input type="password" autoComplete="new-password" maxLength={200} value={nueva} placeholder="Nueva contraseña"
            onChange={(e) => setNueva(e.target.value)} className="rounded-md border border-border px-2 py-1 text-sm" />
          <button type="submit" disabled={!nueva || cambio.isPending}
            className="rounded-md bg-finance px-3 py-1 text-xs font-medium text-white disabled:opacity-50">Guardar</button>
          <button type="button" className="text-xs underline" onClick={() => { setAbierto(false); setNueva(""); }}>Cancelar</button>
          {cambio.isError && <span className="text-xs text-red-700">{cambio.error.message}</span>}
        </form>
      ) : (
        <button type="button" className="text-xs text-finance underline" onClick={() => setAbierto(true)}>
          Cambiar contraseña
        </button>
      )}
    </div>
  );
}
