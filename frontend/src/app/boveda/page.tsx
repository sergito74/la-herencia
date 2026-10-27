"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/auth/AuthContext";
import { BarraAvance, EstadoSincronizacion, SincronizacionAutomatica } from "@/components/boveda/EstadoSincronizacion";
import { PortalForm } from "@/components/boveda/PortalForm";
import { RutinaPanel } from "@/components/boveda/RutinaPanel";
import {
  crearPortal, getPortales, getResumenBoveda, sincronizar, type Portal, type ResultadoSincronizar,
} from "@/services/bovedaApi";

function Acceso({ portal }: { portal: Portal }) {
  const c = portal.credencial;
  if (!c) return <span className="text-xs text-red-700">Sin usuario ni contraseña</span>;
  return (
    <div className="text-xs">
      <div className="text-ink-primary">{c.usuario ?? c.nombre}</div>
      <div className={c.estado === "ok" ? "text-ink-muted" : "text-red-700"}>
        {c.estado === "ok" ? "Contraseña guardada" : c.estado === "rechazada" ? "Contraseña rechazada por el portal" : "Falta la contraseña"}
      </div>
    </div>
  );
}

/** Bóveda de portales (042): accesos, credenciales cifradas y sincronizaciones. Solo Administrador. */
export default function BovedaPage() {
  const { usuario } = useAuth();
  const esAdmin = usuario?.rol === "Administrador";
  const qc = useQueryClient();
  const portales = useQuery({
    queryKey: ["boveda", "portales"],
    queryFn: getPortales,
    enabled: esAdmin,
    // Mientras haya cuentas sincronizándose o en cola, se actualiza cada 1,5 s.
    refetchInterval: (q) => (q.state.data?.items.some((p) => p.enCurso || p.enCola) ? 1500 : false),
  });
  const resumen = useQuery({ queryKey: ["boveda", "resumen"], queryFn: getResumenBoveda, enabled: esAdmin });
  const [seleccion, setSeleccion] = useState<Set<number>>(new Set());
  const [resultado, setResultado] = useState<ResultadoSincronizar | null>(null);
  // Cuentas de la última tanda lanzada desde esta pantalla, para la barra general.
  const [tanda, setTanda] = useState<number[]>([]);
  const [alta, setAlta] = useState(false);

  const lanzar = useMutation({
    mutationFn: (ids?: number[]) => sincronizar(ids),
    onSuccess: (r) => {
      setResultado(r);
      setTanda(r.encolados);
      setSeleccion(new Set());
      qc.invalidateQueries({ queryKey: ["boveda"] });
    },
  });
  const crear = useMutation({
    mutationFn: crearPortal,
    onSuccess: () => { setAlta(false); qc.invalidateQueries({ queryKey: ["boveda"] }); },
  });

  const items = portales.data?.items ?? [];
  const sincronizables = items.filter((p) => !p.motivoNoSincroniza);
  const conAutomatizacion = items.filter((p) => p.conector.disponible).length;
  const ocupadas = items.filter((p) => p.enCurso || p.enCola);
  const enTanda = items.filter((p) => tanda.includes(p.idPortal));
  const terminadas = enTanda.filter((p) => !p.enCurso && !p.enCola).length;
  const tandaActiva = tanda.length > 0 && terminadas < tanda.length;

  // Al terminar la tanda, refrescar contadores y documentos.
  const estabaActiva = useRef(false);
  useEffect(() => {
    if (estabaActiva.current && !tandaActiva) qc.invalidateQueries({ queryKey: ["boveda"] });
    estabaActiva.current = tandaActiva;
  }, [tandaActiva, qc]);

  function alternar(id: number) {
    setSeleccion((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id); else n.add(id);
      return n;
    });
  }

  if (usuario && !esAdmin) {
    return <main className="px-8 py-6 text-sm text-ink-secondary">Solo el administrador accede a la bóveda de portales.</main>;
  }

  const todasMarcadas = sincronizables.length > 0 && sincronizables.every((p) => seleccion.has(p.idPortal));

  return (
    <main className="mx-auto max-w-none space-y-4 px-8 py-6">
      <section className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Bóveda de portales</h1>
          <p className="mt-1 max-w-3xl text-sm text-ink-secondary">
            Accesos a los portales de organismos, proveedores y clientes, con las contraseñas cifradas. Las cuentas con
            sincronización automática bajan facturas y resúmenes a la carpeta de Compras; las demás, por ahora, solo
            guardan el acceso.
          </p>
        </div>
        {!alta && (
          <button type="button" onClick={() => { crear.reset(); setAlta(true); }}
            className="shrink-0 rounded-md border border-border px-4 py-1.5 text-sm">
            Agregar cuenta
          </button>
        )}
      </section>

      {alta && (
        <PortalForm enviando={crear.isPending} error={crear.error?.message ?? null}
          onSubmit={(body) => crear.mutate(body)} onCancel={() => setAlta(false)} />
      )}

      {items.length > 0 && (
        <p className="rounded-md border border-border bg-surface px-3 py-2 text-sm">
          <strong>{conAutomatizacion} de {items.length}</strong> cuentas tienen sincronización automática.
        </p>
      )}

      {resumen.data && resumen.data.total > 0 && (
        <p className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          Para revisar: {[
            resumen.data.conError && `${resumen.data.conError} cuentas con error`,
            resumen.data.requiereIntervencion && `${resumen.data.requiereIntervencion} cuentas que piden intervención`,
            resumen.data.diferenciasSaldo && `${resumen.data.diferenciasSaldo} diferencias de saldo sin revisar`,
            resumen.data.facturasAMano && `${resumen.data.facturasAMano} cuentas con facturas para bajar a mano`,
          ].filter(Boolean).join(" · ")}
        </p>
      )}

      {/* Barra de acciones y avance general */}
      <section className="space-y-3 rounded-md border border-border bg-surface p-3">
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" disabled={seleccion.size === 0 || lanzar.isPending}
            onClick={() => lanzar.mutate([...seleccion])}
            className="rounded-md bg-finance px-4 py-1.5 text-sm font-medium text-white disabled:opacity-40">
            Sincronizar seleccionadas{seleccion.size ? ` (${seleccion.size})` : ""}
          </button>
          <button type="button" disabled={sincronizables.length === 0 || lanzar.isPending}
            onClick={() => lanzar.mutate(undefined)}
            className="rounded-md border border-border px-4 py-1.5 text-sm disabled:opacity-40">
            Sincronizar todas las automáticas ({sincronizables.length})
          </button>
          <span className="text-xs text-ink-muted">Se sincronizan de a una, en orden.</span>
        </div>

        {(tandaActiva || ocupadas.length > 0) && (
          <div className="space-y-1">
            <div className="flex justify-between text-sm">
              <span className="font-medium">
                {tandaActiva ? `Sincronizando: ${terminadas} de ${tanda.length} cuentas terminadas` : `${ocupadas.length} cuenta(s) sincronizándose`}
              </span>
              {tandaActiva && <span className="text-ink-secondary">{Math.round((terminadas / tanda.length) * 100)}%</span>}
            </div>
            <BarraAvance hecho={tandaActiva ? terminadas : null} total={tandaActiva ? tanda.length : null} />
          </div>
        )}

        {!tandaActiva && tanda.length > 0 && ocupadas.length === 0 && (
          <p className="text-sm text-agro">
            ✓ Terminó la sincronización de {tanda.length} cuenta(s): {enTanda.filter((p) => p.ultimaCorrida?.estado === "ok").length} bien
            {enTanda.some((p) => p.ultimaCorrida && p.ultimaCorrida.estado !== "ok") &&
              `, ${enTanda.filter((p) => p.ultimaCorrida && p.ultimaCorrida.estado !== "ok").length} con problemas (ver cada fila)`}.
          </p>
        )}
        {resultado && resultado.encolados.length === 0 && resultado.omitidos.length === 0 && (
          <p className="text-sm text-ink-secondary">No había cuentas para sincronizar.</p>
        )}
        {resultado && resultado.omitidos.length > 0 && (
          <details className="text-sm text-ink-secondary">
            <summary className="cursor-pointer">
              {resultado.omitidos.length} cuenta(s) no se sincronizaron — ver por qué
            </summary>
            <ul className="mt-1 list-disc pl-5 text-xs">
              {resultado.omitidos.map((o) => <li key={o.idPortal}><strong>{o.nombre}</strong>: {o.motivo}</li>)}
            </ul>
          </details>
        )}
        {lanzar.isError && <p className="text-sm text-red-700">{lanzar.error.message}</p>}
      </section>

      <RutinaPanel />

      {portales.isError && <p className="text-sm text-red-700">No se pudo leer la bóveda: {portales.error.message}</p>}
      <div className="overflow-x-auto rounded-md border border-border bg-surface">
        <table className="min-w-full text-sm">
          <thead className="bg-surface-sunken text-left text-xs text-ink-secondary">
            <tr>
              <th className="w-8 px-3 py-2">
                <input type="checkbox" aria-label="Seleccionar todas las sincronizables" checked={todasMarcadas}
                  disabled={sincronizables.length === 0}
                  onChange={() => setSeleccion(todasMarcadas ? new Set() : new Set(sincronizables.map((p) => p.idPortal)))} />
              </th>
              <th className="px-3 py-2">Cuenta</th>
              <th className="px-3 py-2">Acceso</th>
              <th className="px-3 py-2">Sincronización automática</th>
              <th className="px-3 py-2">Estado</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {items.map((p) => {
              const puede = !p.motivoNoSincroniza && !p.enCurso && !p.enCola;
              return (
                <tr key={p.idPortal} className={`border-t border-border align-top ${p.enCurso ? "bg-finance-light/40" : ""}`}>
                  <td className="px-3 py-2">
                    <input type="checkbox" aria-label={`Seleccionar ${p.nombre}`} disabled={!puede}
                      title={p.motivoNoSincroniza ?? (p.enCurso || p.enCola ? "Ya se está sincronizando" : undefined)}
                      checked={seleccion.has(p.idPortal)} onChange={() => alternar(p.idPortal)} />
                  </td>
                  <td className="px-3 py-2">
                    <Link href={`/boveda/${p.idPortal}`} className="font-medium text-finance hover:underline">{p.nombre}</Link>
                    <div className="text-xs text-ink-muted">{p.contacto ?? p.tipo}</div>
                  </td>
                  <td className="px-3 py-2"><Acceso portal={p} /></td>
                  <td className="px-3 py-2"><SincronizacionAutomatica portal={p} /></td>
                  <td className="px-3 py-2"><EstadoSincronizacion portal={p} /></td>
                  <td className="px-3 py-2 text-right">
                    <a href={p.url} target="_blank" rel="noopener noreferrer" className="text-xs text-finance underline">
                      Abrir portal
                    </a>
                  </td>
                </tr>
              );
            })}
            {portales.data && items.length === 0 && (
              <tr><td colSpan={6} className="px-3 py-4 text-center text-ink-muted">Todavía no hay cuentas registradas.</td></tr>
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
