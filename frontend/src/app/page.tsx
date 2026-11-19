"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { ButtonLink } from "@/components/ui/Button";
import { CultivoChip } from "@/components/cultivos/CultivoChip";
import { formatCantidad, formatFecha, formatMoneda } from "@/lib/format";
import { fetchInicio, type Pendiente, type ResumenInicio } from "@/services/inicioApi";
import { apiGet } from "@/services/apiClient";

const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const mes = (p: string) => { const m = p.match(/^(\d{4})-(\d{2})/); return m ? MESES[Number(m[2]) - 1] : p; };
const millones = (v: number) => `${v < 0 ? "-" : ""}$ ${formatCantidad(Math.round(Math.abs(v) / 100000) / 10)} M`;

function saludo(): string {
  const h = new Date().getHours();
  return h < 13 ? "Buen día" : h < 20 ? "Buenas tardes" : "Buenas noches";
}

function Esqueleto({ alto = "h-24" }: { alto?: string }) {
  return <div className={`${alto} animate-pulse rounded-lg border border-border bg-surface`} />;
}

/** Lista de pendientes accionables: cada uno lleva a donde se resuelve (spec 051 FR-001…003). */
function ParaHacerHoy({ pendientes, listo }: { pendientes: Pendiente[]; listo: boolean }) {
  if (!listo) return <Esqueleto alto="h-56" />;
  const reales = pendientes.filter((p) => !p.error);
  return (
    <section className="rounded-lg border border-border bg-surface shadow-sm">
      <header className="flex items-center justify-between border-b border-border px-5 py-3">
        <h2 className="text-base font-semibold text-ink-primary">Para hacer hoy</h2>
        {reales.length > 0 && <span className="text-sm text-ink-secondary">{reales.length} {reales.length === 1 ? "tema" : "temas"}</span>}
      </header>
      {reales.length === 0 && !pendientes.some((p) => p.error) ? (
        <div className="flex items-center gap-3 px-5 py-6 text-sm">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-status-success-bg text-status-success" aria-hidden>✓</span>
          <div><p className="font-medium text-ink-primary">Todo al día</p><p className="text-ink-secondary">No hay nada pendiente para resolver.</p></div>
        </div>
      ) : (
        <ul className="divide-y divide-border">
          {pendientes.map((p) => (
            <li key={p.clave}>
              <Link href={p.destino} className="group flex items-center gap-4 px-5 py-3 transition-colors hover:bg-surface-sunken/60">
                <span className={`flex h-9 min-w-[2.25rem] items-center justify-center rounded-md px-2 font-data text-sm font-semibold ${p.error ? "bg-surface-sunken text-ink-muted" : "bg-finance-light text-finance"}`}>
                  {p.error ? "?" : formatCantidad(p.cantidad ?? 0)}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-medium text-ink-primary">{p.error ? `${p.texto}: no se pudo calcular` : p.texto}</span>
                  {p.detalle && <span className="block truncate text-xs text-ink-secondary">{p.detalle}</span>}
                </span>
                {p.importe ? <span className="hidden font-data text-sm text-ink-secondary sm:block">{formatMoneda(p.importe)}</span> : null}
                <span className="text-ink-muted transition-transform group-hover:translate-x-0.5 group-hover:text-finance" aria-hidden>→</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function Indicador({ titulo, valor, pie, href, error }: { titulo: string; valor: React.ReactNode; pie?: React.ReactNode; href: string; error?: boolean }) {
  return (
    <Link href={href} className="rounded-lg border border-border bg-surface p-4 shadow-sm transition hover:border-border-strong hover:shadow">
      <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">{titulo}</p>
      <p className="mt-1 font-data text-xl font-semibold text-ink-primary">{error ? "—" : valor}</p>
      {pie && <p className="mt-0.5 text-xs text-ink-secondary">{error ? "no se pudo calcular" : pie}</p>}
    </Link>
  );
}

function Indicadores({ d }: { d: ResumenInicio }) {
  // 19/11/2026: inversiones (plazos fijos y Fondo Fima), con el rendimiento del ejercicio.
  const inv = useQuery({ queryKey: ["tesoreria-inversiones"], queryFn: () => apiGet<{ invertido: number; rendimientoEjercicio: number; ejercicioActual: string }>("/api/tesoreria/inversiones") });
  const i = d.indicadores ?? {};
  const b = i.bancos, de = i.deuda, s = i.stock, c = i.cajas;
  const fecha = b?.cuentas ? Object.values(b.cuentas).map((x) => x.fecha).sort().at(-1) : undefined;
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
      <Indicador titulo="Disponible en bancos" href="/finanzas/tesoreria" error={b?.error} valor={formatMoneda(b?.total ?? 0)}
        pie={fecha ? `Nación + Galicia, al ${formatFecha(fecha)}` : "Nación + Galicia"} />
      <Indicador titulo="Deuda con proveedores" href="/finanzas/cuentas-corrientes/saldos" error={de?.error} valor={formatMoneda(de?.pesos ?? 0)}
        pie={`${de?.dolares ? `${formatMoneda(de.dolares, "Dolares")} · ` : ""}${de?.proveedores ?? 0} proveedores`} />
      <Indicador titulo="Stock valuado" href="/produccion/stock" error={s?.error} valor={formatMoneda(s?.valor ?? 0)} pie={`${s?.productos ?? 0} productos en depósito`} />
      <Indicador titulo="Inversiones" href="/finanzas/tesoreria?medio=inversiones" error={inv.isError} valor={formatMoneda(inv.data?.invertido ?? 0)}
        pie={inv.data ? `rendimiento ${inv.data.ejercicioActual}: ${formatMoneda(inv.data.rendimientoEjercicio)}` : "…"} />
      <Indicador titulo="Cajas" href="/finanzas/cajas" error={c?.error} valor={formatMoneda(c?.pesos ?? 0)} pie={c?.dolares ? `y ${formatMoneda(c.dolares, "Dolares")}` : "Giamigli y caja chica"} />
    </div>
  );
}

/** Neto del flujo de caja de los últimos meses, en barras chicas (FR-005). */
function Flujo({ flujo }: { flujo: ResumenInicio["flujo"] }) {
  const datos = Array.isArray(flujo) ? flujo : [];
  const max = Math.max(1, ...datos.map((p) => Math.abs(p.neto)));
  return (
    <section className="rounded-lg border border-border bg-surface p-4 shadow-sm">
      <header className="mb-3 flex items-baseline justify-between">
        <h2 className="text-sm font-semibold text-ink-primary">Flujo de caja · últimos 6 meses</h2>
        <Link href="/finanzas/flujo-caja-real" className="text-xs font-medium text-finance hover:underline">Ver flujo →</Link>
      </header>
      {!datos.length ? <p className="text-sm text-ink-muted">{Array.isArray(flujo) ? "Sin movimientos." : "No se pudo calcular."}</p> : (
        <div className="flex h-36 items-stretch gap-3">
          {datos.map((p) => {
            const alto = Math.max(4, Math.round((Math.abs(p.neto) / max) * 50));
            return (
              <div key={p.periodo} className="flex flex-1 flex-col items-center" title={`${mes(p.periodo)}: ${formatMoneda(p.neto)}`}>
                <div className="flex h-1/2 w-full items-end justify-center">{p.neto >= 0 && <div className="w-full max-w-[2.5rem] rounded-t bg-status-success/70" style={{ height: `${alto * 2}%` }} />}</div>
                <div className="flex h-1/2 w-full items-start justify-center border-t border-border">{p.neto < 0 && <div className="w-full max-w-[2.5rem] rounded-b bg-ink-muted/50" style={{ height: `${alto * 2}%` }} />}</div>
                <span className="mt-1 text-[11px] text-ink-secondary">{mes(p.periodo)}</span>
                <span className="font-data text-[11px] text-ink-muted">{millones(p.neto)}</span>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

function Campania({ c }: { c: ResumenInicio["campania"] }) {
  return (
    <section className="rounded-lg border border-border bg-surface p-4 shadow-sm">
      <header className="mb-3 flex items-baseline justify-between">
        <h2 className="text-sm font-semibold text-ink-primary">Campaña {c?.nombre ?? ""}</h2>
        <Link href="/produccion/planificacion" className="text-xs font-medium text-finance hover:underline">Ver plan →</Link>
      </header>
      {c?.error ? <p className="text-sm text-ink-muted">No se pudo calcular.</p> : <>
        <div className="flex flex-wrap gap-2">
          {(c?.cultivos ?? []).map((x) => <span key={x.cultivo} className="inline-flex items-center gap-1.5 text-sm"><CultivoChip cultivo={x.cultivo} /><span className="font-data text-ink-secondary">{formatCantidad(x.ha)} ha</span></span>)}
        </div>
        <ul className="mt-3 space-y-1 border-t border-border pt-3 text-sm">
          {(c?.ordenes ?? []).map((o) => <li key={o.id}><Link href={`/produccion/ordenes/${o.id}/editar`} className="flex justify-between gap-3 hover:text-finance">
            <span>Orden {o.id} · {o.labor ?? "—"}</span><span className="text-ink-secondary">{formatFecha(o.fecha)} · {o.estado}</span></Link></li>)}
        </ul>
      </>}
    </section>
  );
}

export default function Home() {
  const { data } = useQuery({ queryKey: ["inicio"], queryFn: () => fetchInicio(), refetchInterval: (q) => (q.state.data?.listo ? 5 * 60_000 : 4_000) });
  const d: ResumenInicio = data ?? { listo: false, actualizando: true };
  const hoy = new Date().toLocaleDateString("es-AR", { weekday: "long", day: "numeric", month: "long" });

  return (
    <main className="mx-auto max-w-none space-y-4 px-6 py-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-ink-primary">{saludo()}</h1>
          <p className="text-sm text-ink-secondary first-letter:uppercase">{hoy}{d.calculado ? ` · actualizado ${d.calculado.slice(11, 16)} h` : ""}{d.actualizando && d.listo ? " · actualizando…" : ""}</p>
        </div>
        <SoloLectura>
          <div className="flex flex-wrap gap-2">
            <ButtonLink href="/compras/nueva" variant="primary">+ Nueva compra</ButtonLink>
            <ButtonLink href="/produccion/ordenes/nuevo">+ Nueva orden</ButtonLink>
            <ButtonLink href="/finanzas/cajas">Movimiento de caja</ButtonLink>
            <ButtonLink href="/personal/trabajos-eventuales">Trabajo eventual</ButtonLink>
            <ButtonLink href="/produccion/ordenes">Leer planilla de Matías</ButtonLink>
          </div>
        </SoloLectura>
      </header>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <ParaHacerHoy pendientes={d.pendientes ?? []} listo={d.listo} />
        <div className="space-y-4">
          {d.listo ? <Flujo flujo={d.flujo} /> : <Esqueleto alto="h-48" />}
          {d.listo ? <Campania c={d.campania} /> : <Esqueleto alto="h-40" />}
        </div>
      </div>

      {d.listo ? <Indicadores d={d} /> : <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">{[0, 1, 2, 3].map((k) => <Esqueleto key={k} />)}</div>}
      {!d.listo && <p className="text-center text-xs text-ink-muted">Preparando el resumen del día… (la primera vez tarda alrededor de un minuto)</p>}
    </main>
  );
}
