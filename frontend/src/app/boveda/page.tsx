"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { useAuth } from "@/components/auth/AuthContext";
import { PortalForm } from "@/components/boveda/PortalForm";
import { formatFechaHora } from "@/lib/format";
import { correrTodos, crearPortal, getPortales, getResumenBoveda, type Portal } from "@/services/bovedaApi";

function EstadoCredencial({ portal }: { portal: Portal }) {
  const c = portal.credencial;
  if (!c) return <span className="text-ink-muted">Sin credencial</span>;
  const color = c.estado === "ok" ? "text-ink-secondary" : "text-red-700";
  const texto = c.estado === "ok" ? "••••••••" : c.estado === "rechazada" ? "Rechazada por el portal" : "Falta contraseña";
  return (
    <span>
      <span className="text-ink-primary">{c.usuario ?? c.nombre}</span>{" "}
      <span className={`font-mono text-xs ${color}`}>{texto}</span>
    </span>
  );
}

function EstadoDescarga({ portal }: { portal: Portal }) {
  if (!portal.conector.disponible) return <span className="rounded bg-surface-sunken px-1.5 py-0.5 text-xs">Solo bóveda</span>;
  if (!portal.autorizacion.vigente) return <span className="text-xs text-red-700">Sin autorización</span>;
  const p = portal.programacion;
  if (portal.enCurso) return <span className="text-xs text-finance">Corriendo…</span>;
  if (p?.suspendida) return <span className="text-xs text-red-700">Suspendida: {p.motivoSuspension}</span>;
  if (!p || p.frecuencia === "desactivada") return <span className="text-xs text-ink-muted">Sin programar</span>;
  return <span className="text-xs text-ink-secondary">Próxima: {formatFechaHora(p.proximaCorrida)}</span>;
}

/** Bóveda de portales (042): accesos, credenciales cifradas y descargas
 * programadas. Solo para el Administrador. */
export default function BovedaPage() {
  const { usuario } = useAuth();
  const esAdmin = usuario?.rol === "Administrador";
  const qc = useQueryClient();
  const portales = useQuery({
    queryKey: ["boveda", "portales"],
    queryFn: getPortales,
    enabled: esAdmin,
    refetchInterval: (q) => (q.state.data?.items.some((p) => p.enCurso) ? 3000 : false),
  });
  const resumen = useQuery({ queryKey: ["boveda", "resumen"], queryFn: getResumenBoveda, enabled: esAdmin });
  const todos = useMutation({ mutationFn: correrTodos, onSuccess: () => qc.invalidateQueries({ queryKey: ["boveda"] }) });
  const [alta, setAlta] = useState(false);
  const crear = useMutation({
    mutationFn: crearPortal,
    onSuccess: () => {
      setAlta(false);
      qc.invalidateQueries({ queryKey: ["boveda"] });
    },
  });

  if (usuario && !esAdmin) {
    return (
      <main className="mx-auto max-w-none px-8 py-6">
        <p className="text-sm text-ink-secondary">Solo el administrador accede a la bóveda de portales.</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-none space-y-4 px-8 py-6">
      <section className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Bóveda de portales</h1>
          <p className="mt-1 text-sm text-ink-secondary">
            Accesos a portales de organismos, proveedores y clientes. Las contraseñas se guardan cifradas. El sistema
            solo entra a los portales autorizados, para consultar y descargar.
          </p>
        </div>
        <div className="flex shrink-0 gap-2">
          <button type="button" disabled={todos.isPending} onClick={() => todos.mutate()}
            title="Corre uno por vez los portales autorizados con descarga automática"
            className="rounded-md border border-border px-4 py-1.5 text-sm disabled:opacity-50">
            Correr todos ahora
          </button>
          {!alta && (
            <button type="button" onClick={() => { crear.reset(); setAlta(true); }}
              className="rounded-md bg-finance px-4 py-1.5 text-sm font-medium text-white">
              Agregar portal
            </button>
          )}
        </div>
      </section>

      {resumen.data && resumen.data.total > 0 && (
        <p className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          Para revisar: {[
            resumen.data.pendientesCarga && `${resumen.data.pendientesCarga} documentos pendientes de carga`,
            resumen.data.conError && `${resumen.data.conError} portales con error`,
            resumen.data.requiereIntervencion && `${resumen.data.requiereIntervencion} portales que piden intervención`,
            resumen.data.diferenciasSaldo && `${resumen.data.diferenciasSaldo} diferencias de saldo sin revisar`,
          ].filter(Boolean).join(" · ")}
        </p>
      )}

      {alta && (
        <PortalForm enviando={crear.isPending} error={crear.error?.message ?? null}
          onSubmit={(body) => crear.mutate(body)} onCancel={() => setAlta(false)} />
      )}

      {portales.isError && <p className="text-sm text-red-700">No se pudo leer la bóveda: {portales.error.message}</p>}
      <div className="overflow-x-auto rounded-md border border-border bg-surface">
        <table className="min-w-full text-sm">
          <thead className="bg-surface-sunken text-left text-xs text-ink-secondary">
            <tr>
              <th className="px-3 py-2">Portal</th>
              <th className="px-3 py-2">Contacto</th>
              <th className="px-3 py-2">Credencial</th>
              <th className="px-3 py-2">Descarga</th>
              <th className="px-3 py-2">Última corrida</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {(portales.data?.items ?? []).map((p) => (
              <tr key={p.idPortal} className="border-t border-border">
                <td className="px-3 py-2">
                  <Link href={`/boveda/${p.idPortal}`} className="font-medium text-finance hover:underline">{p.nombre}</Link>
                  <div className="text-xs text-ink-muted">{p.tipo}</div>
                </td>
                <td className="px-3 py-2">{p.contacto ?? "—"}</td>
                <td className="px-3 py-2"><EstadoCredencial portal={p} /></td>
                <td className="px-3 py-2"><EstadoDescarga portal={p} /></td>
                <td className="px-3 py-2 text-xs">
                  {p.ultimaCorrida ? `${formatFechaHora(p.ultimaCorrida.inicio)} · ${p.ultimaCorrida.estado}` : "—"}
                </td>
                <td className="px-3 py-2 text-right">
                  <a href={p.url} target="_blank" rel="noopener noreferrer" className="text-xs text-finance underline">
                    Abrir portal
                  </a>
                </td>
              </tr>
            ))}
            {portales.data && portales.data.items.length === 0 && (
              <tr><td colSpan={6} className="px-3 py-4 text-center text-ink-muted">Todavía no hay portales registrados.</td></tr>
            )}
            {portales.isLoading && (
              <tr><td colSpan={6} className="px-3 py-4 text-center text-ink-muted">Cargando…</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}
