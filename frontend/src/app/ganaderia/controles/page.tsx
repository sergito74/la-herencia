"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { MarcaRevisado } from "@/components/ui/MarcaRevisado";
import { PageHeader } from "@/components/ui/PageHeader";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatFechaHora } from "@/lib/format";
import { apiGet, apiPost } from "@/services/apiClient";

interface Caso { tipo: string; clave: string; texto: string; enlace: string | null }
interface Grupo { grupo: string; items: Caso[]; cantidad: number; error: string | null }
interface Aceptado { id: number; tipo: string; clave: string; motivo: string; usuario: string | null; fecha: string }
interface Controles { corrido: string; grupos: Grupo[]; aceptados: Aceptado[] }

const NOMBRE: Record<string, string> = {
  venta_sin_dato: "Venta sin cabezas o sin kg", venta_kg_cabeza: "Kg por cabeza fuera de rango",
  venta_renglon_repetido: "Renglones idénticos", venta_negativo_sin_par: "Negativo sin su par",
  consignatario_saldo: "Consignatario con saldo", stock_negativo: "Existencia negativa",
  stock_recuento: "Recuento distinto de lo esperado", pastaje_sin_liquidar: "Mes sin liquidar",
  pastaje_facturado: "Facturado distinto de lo liquidado", imputacion_sin_centro: "Renglón sin centro de costos",
  imputacion_contradictoria: "Centro e imputación contradictorios", imputacion_ganaderia_pendiente: "Compra de Ganadería sin imputar",
  imputacion_fracciones: "Imputado distinto del renglón", reserva_sin_consumo: "Reserva sin consumo registrado",
};

/** 052 US5: controles ganaderos por grupo; cada caso se revisa y acepta con motivo. */
export default function ControlesGanaderosPage() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["ganaderia", "controles"], queryFn: () => apiGet<Controles>("/api/ganaderia/controles") });
  const correr = useMutation({
    mutationFn: () => apiPost<Controles>("/api/ganaderia/controles/correr", {}),
    onSuccess: (d) => qc.setQueryData(["ganaderia", "controles"], d),
  });
  const quitar = useMutation({
    mutationFn: (id: number) => apiPost(`/api/ganaderia/controles/aceptados/${id}/quitar`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ganaderia", "controles"] }),
  });
  const aceptar = async (c: Caso, motivo: string) => {
    await apiPost("/api/ganaderia/controles/aceptar", { tipo: c.tipo, clave: c.clave, motivo });
    await qc.invalidateQueries({ queryKey: ["ganaderia", "controles"] });
  };

  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Controles ganaderos"
        ayuda="Ventas, consignatarios, stock, pastaje, imputación y forrajes. Lo revisado se marca como aceptado con su motivo y deja de aparecer; la marca se puede quitar.">
        <button type="button" disabled={correr.isPending} onClick={() => correr.mutate()}
          className="rounded-md bg-finance px-2.5 py-1 text-sm text-white hover:opacity-90 disabled:opacity-50">
          {correr.isPending ? "Corriendo…" : "Correr controles ahora"}
        </button>
      </PageHeader>
      {q.isLoading || correr.isPending ? <LoadingState rows={8} />
        : q.isError || !q.data ? <ErrorState message="No se pudieron correr los controles." onRetry={() => q.refetch()} />
        : (
          <>
            <p className="mb-3 text-sm text-ink-secondary">Último control: {formatFechaHora(q.data.corrido)}</p>
            <div className="space-y-3">
              {q.data.grupos.map((g) => (
                <details key={g.grupo} open={g.cantidad > 0 && g.cantidad <= 15} className="rounded-md border border-border bg-surface">
                  <summary className="cursor-pointer px-3 py-2 text-sm font-semibold">
                    {g.grupo}{" "}
                    <span className={g.cantidad ? "text-status-danger" : "text-status-success"}>({g.cantidad})</span>
                    {g.error && <span className="ml-2 font-normal text-status-danger">No se pudo correr: {g.error}</span>}
                  </summary>
                  {g.items.length > 0 && (
                    <ul className="divide-y divide-border/60 text-sm">
                      {g.items.map((c) => (
                        <li key={c.tipo + c.clave} className="flex flex-wrap items-center justify-between gap-2 px-3 py-1.5">
                          <span>
                            <span className="text-ink-secondary">{NOMBRE[c.tipo] ?? c.tipo}: </span>
                            {c.enlace ? <Link href={c.enlace} className="hover:underline">{c.texto}</Link> : c.texto}
                          </span>
                          <MarcaRevisado detalle={c.texto} onAceptar={(motivo) => aceptar(c, motivo)} />
                        </li>
                      ))}
                    </ul>
                  )}
                </details>
              ))}
            </div>
            {q.data.aceptados.length > 0 && (
              <details className="mt-4 rounded-md border border-border bg-surface text-sm">
                <summary className="cursor-pointer px-3 py-2 font-medium">Revisados y aceptados ({q.data.aceptados.length})</summary>
                <ul className="divide-y divide-border/60">
                  {q.data.aceptados.map((a) => (
                    <li key={a.id} className="flex flex-wrap items-center justify-between gap-2 px-3 py-1.5">
                      <span>
                        <strong>{NOMBRE[a.tipo] ?? a.tipo}</strong> — {a.motivo}
                        <span className="text-xs text-ink-secondary"> ({a.usuario ?? "—"}, {formatFechaHora(a.fecha)})</span>
                      </span>
                      <SoloLectura>
                        <button type="button" disabled={quitar.isPending} className="text-xs text-ink-secondary underline"
                          onClick={() => quitar.mutate(a.id)}>Quitar la marca</button>
                      </SoloLectura>
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </>
        )}
    </main>
  );
}
