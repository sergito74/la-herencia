"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/components/auth/AuthContext";
import { CorridasTabla } from "@/components/boveda/CorridasTabla";
import { DocumentosTabla } from "@/components/boveda/DocumentosTabla";
import { BackLink } from "@/components/ui/BackLink";
import { formatFechaHora } from "@/lib/format";
import { ETIQUETA_CORRIDA } from "@/services/bovedaApi";
import { getCorridas, getDocumentos, getEstado, iniciarDescarga } from "@/services/descargaPeajesApi";

/** Compras › Descarga de peajes (037): TelepeajePlus, TelePASE, CEAMSE y AUBASA.
 * Desde 042 las credenciales, autorizaciones y la programación viven en la
 * Bóveda de portales (solo Administrador); esta vista conserva el permiso de Compras. */
export default function DescargaPeajesPage() {
  const { usuario } = useAuth();
  const qc = useQueryClient();
  const estado = useQuery({
    queryKey: ["descarga-peajes", "estado"],
    queryFn: getEstado,
    refetchInterval: (q) => (q.state.data?.enCurso ? 2000 : false),
  });
  const enCurso = estado.data?.enCurso ?? false;
  const pendientes = useQuery({
    queryKey: ["descarga-peajes", "documentos", "pendiente", enCurso],
    queryFn: () => getDocumentos("pendiente"),
  });
  const recientes = useQuery({
    queryKey: ["descarga-peajes", "documentos", "todos", enCurso],
    queryFn: () => getDocumentos(undefined, 20),
  });
  const corridas = useQuery({ queryKey: ["descarga-peajes", "corridas", enCurso], queryFn: () => getCorridas(40) });
  const descargar = useMutation({
    mutationFn: iniciarDescarga,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["descarga-peajes"] }),
  });
  const puedeDescargar = usuario?.rol !== "Lectura";

  return (
    <main className="mx-auto max-w-none space-y-4 px-8 py-6">
      <BackLink href="/compras">Volver a Compras</BackLink>
      <section className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Descarga de peajes</h1>
          <p className="mt-1 text-sm text-ink-secondary">
            Las facturas se cargan solas en Compras cuando lo leído cierra al centavo con el total impreso; si no,
            quedan pendientes con el motivo.
            {usuario?.rol === "Administrador" && (
              <> Credenciales y programación: <Link href="/boveda" className="text-finance underline">Bóveda de portales</Link>.</>
            )}
          </p>
        </div>
        {puedeDescargar && (
          <button type="button" disabled={enCurso || descargar.isPending} onClick={() => descargar.mutate()}
            className="shrink-0 rounded-md bg-finance px-4 py-1.5 text-sm font-medium text-white disabled:opacity-50">
            {enCurso ? "Descargando…" : "Descargar ahora"}
          </button>
        )}
      </section>
      {descargar.isError && <p className="text-sm text-red-700">{descargar.error.message}</p>}
      {estado.isError && <p className="text-sm text-red-700">No se pudo leer el estado de la descarga.</p>}

      <section className="rounded-md border border-border bg-surface p-4">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-ink-muted">
              <th className="py-2 pr-3">Portal</th>
              <th className="py-2 pr-3">Configuración</th>
              <th className="py-2 pr-3">Última corrida</th>
              <th className="py-2 pr-3">Próxima corrida</th>
            </tr>
          </thead>
          <tbody>
            {(estado.data?.portales ?? []).map((p) => (
              <tr key={p.idPortal} className="border-b border-border/60">
                <td className="py-2 pr-3">{p.portal}</td>
                <td className="py-2 pr-3">
                  {!p.autorizado ? <span className="text-red-700">Sin autorización</span>
                    : !p.credenciales ? <span className="text-red-700">Faltan o fueron rechazadas las credenciales</span>
                    : "Lista"}
                </td>
                <td className="py-2 pr-3">
                  {p.ultimaCorrida
                    ? `${formatFechaHora(p.ultimaCorrida.inicio)} · ${ETIQUETA_CORRIDA[p.ultimaCorrida.estado] ?? p.ultimaCorrida.estado}`
                    : "—"}
                </td>
                <td className="py-2 pr-3">{p.proximaCorrida ? formatFechaHora(p.proximaCorrida) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-2 text-xs text-ink-muted">Las corridas programadas ocurren con la aplicación abierta.</p>
      </section>

      <section className="rounded-md border border-border bg-surface p-4">
        <h2 className="mb-2 text-base font-semibold">Pendientes de carga manual</h2>
        <DocumentosTabla documentos={pendientes.data?.items ?? []}
          vacio={pendientes.isLoading ? "Cargando…" : "No hay documentos pendientes."} conPortal />
      </section>
      <section className="rounded-md border border-border bg-surface p-4">
        <h2 className="mb-2 text-base font-semibold">Últimos documentos</h2>
        <DocumentosTabla documentos={recientes.data?.items ?? []} vacio="Todavía no se bajaron documentos." conPortal />
      </section>
      <section className="rounded-md border border-border bg-surface p-4">
        <h2 className="mb-2 text-base font-semibold">Corridas</h2>
        <CorridasTabla corridas={corridas.data?.items ?? []} conPortal />
      </section>
    </main>
  );
}
