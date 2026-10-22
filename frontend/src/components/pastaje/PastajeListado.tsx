"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { KpiCard } from "@/components/ui/KpiCard";
import { SideDrawer } from "@/components/ui/SideDrawer";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatCantidad, formatFecha } from "@/lib/format";
import { listarContratos } from "@/services/pastajeApi";

import { ContratoForm } from "./ContratoForm";
import { btnPrimario, indice, pesos, tarifaTexto, tonoContrato } from "./comunes";

function destinoPaso(paso: string, id: number): string {
  if (paso.startsWith("Cargar factura") || paso.startsWith("Cobro")) return `/ventas/pastaje/${id}?tab=facturas`;
  return `/ventas/pastaje/${id}?tab=liquidaciones`;
}

export function PastajeListado() {
  const router = useRouter();
  const [estado, setEstado] = useState<"vigente" | "finalizado" | "">("vigente");
  const [alta, setAlta] = useState(false);
  const q = useQuery({ queryKey: ["pastaje", "contratos", estado], queryFn: () => listarContratos(estado || undefined) });
  const contratos = q.data ?? [];
  const cabezas = contratos.reduce((s, c) => s + c.cabezasActuales.reduce((a, x) => a + x.cabezas, 0), 0);
  const estimado = contratos.reduce((s, c) => s + Number(c.estimadoMesCurso ?? 0), 0);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <label className="text-sm">
          Estado{" "}
          <select className="ml-2 rounded-sm border border-border bg-surface px-2 py-1" value={estado} onChange={(e) => setEstado(e.target.value as typeof estado)}>
            <option value="vigente">Vigentes</option>
            <option value="finalizado">Finalizados</option>
            <option value="">Todos</option>
          </select>
        </label>
        <SoloLectura>
          <button className={btnPrimario} onClick={() => setAlta(true)}>
            + Nuevo contrato
          </button>
        </SoloLectura>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <KpiCard label="Contratos" value={String(contratos.length)} />
        <KpiCard label="Cabezas en el campo" value={formatCantidad(cabezas)} />
        <KpiCard label="Estimado del mes (neto)" value={pesos(estimado)} />
        <KpiCard
          label="Contratos con alertas"
          value={String(contratos.filter((c) => c.alertas.length).length)}
          tone={contratos.some((c) => c.alertas.length) ? "warning" : "neutral"}
        />
      </div>

      {q.isLoading && <LoadingState />}
      {q.isError && <ErrorState message={(q.error as Error).message} onRetry={() => q.refetch()} />}
      {q.isSuccess && contratos.length === 0 && <EmptyState message="No hay contratos de pastaje en este estado." />}

      <div className="grid gap-4 lg:grid-cols-2">
        {contratos.map((c) => (
          <article key={c.id} className="rounded-md border border-border bg-surface p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <Link href={`/ventas/pastaje/${c.id}`} className="text-lg font-semibold hover:underline">
                  {c.cliente}
                </Link>
                <p className="text-sm text-ink-secondary">
                  {c.establecimiento ?? "La Herencia"} · desde {formatFecha(c.fechaInicio)}
                  {c.fechaFin ? ` hasta ${formatFecha(c.fechaFin)}` : ""}
                </p>
              </div>
              <StatusBadge label={c.estado} tone={tonoContrato(c.estado)} />
            </div>
            <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              <dt className="text-ink-secondary">Hacienda</dt>
              <dd className="font-data">
                {c.cabezasActuales.length ? c.cabezasActuales.map((x) => `${formatCantidad(x.cabezas)} ${x.categoria}`).join(" · ") : "Sin hacienda"}
              </dd>
              <dt className="text-ink-secondary">Tarifa</dt>
              <dd>{c.tarifas.map((t) => tarifaTexto(t)).join(" · ")}</dd>
              <dt className="text-ink-secondary">Último INMAG</dt>
              <dd className="font-data">{c.inmagUltimo ? `${indice(c.inmagUltimo.indice)} (${formatFecha(c.inmagUltimo.fecha)})` : "—"}</dd>
              <dt className="text-ink-secondary">Promedio del mes</dt>
              <dd className="font-data">{indice(c.promedioMesCurso)}</dd>
              <dt className="text-ink-secondary">Estimado del mes</dt>
              <dd className="font-data">{pesos(c.estimadoMesCurso)}</dd>
            </dl>
            {c.alertas.length > 0 && (
              <ul className="mt-3 space-y-1" aria-label="Alertas">
                {c.alertas.map((a, i) => (
                  <li key={i} className="rounded-sm bg-status-warning-bg px-2 py-1 text-xs text-status-warning">
                    ⚠ {a}
                  </li>
                ))}
              </ul>
            )}
            <div className="mt-4 flex gap-3">
              {c.proximoPaso ? (
                <Link className={btnPrimario} href={destinoPaso(c.proximoPaso, c.id)}>
                  {c.proximoPaso}
                </Link>
              ) : (
                <span className="text-sm text-ink-secondary">Al día</span>
              )}
              <Link className="self-center text-sm underline" href={`/ventas/pastaje/${c.id}`}>
                Ver condiciones
              </Link>
            </div>
          </article>
        ))}
      </div>

      <SideDrawer open={alta} onClose={() => setAlta(false)} title="Nuevo contrato de pastaje" maxWidthClass="max-w-2xl">
        <ContratoForm onListo={(c) => router.push(`/ventas/pastaje/${c.id}?tab=bitacora`)} />
      </SideDrawer>
    </div>
  );
}
