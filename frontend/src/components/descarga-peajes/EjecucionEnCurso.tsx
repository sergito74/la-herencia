"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { DocumentosLista } from "@/components/descarga-peajes/DocumentosLista";
import { ApiError } from "@/services/apiClient";
import {
  ETIQUETA_EJECUCION,
  ETIQUETA_PORTAL,
  getEjecucion,
  iniciarDescarga,
  type EstadoConfiguracion,
  type PortalResultado,
} from "@/services/descargaPeajesApi";

const COLOR_PORTAL: Record<string, string> = {
  pendiente: "text-ink-muted",
  en_curso: "text-finance",
  ok: "text-agro",
  error: "text-red-700",
  sin_credenciales: "text-amber-700",
};

export function TablaPortales({ portales }: { portales: PortalResultado[] }) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-ink-muted">
          <th className="py-2 pr-3">Portal</th>
          <th className="py-2 pr-3">Estado</th>
          <th className="py-2 pr-3 text-right">Nuevos</th>
          <th className="py-2 pr-3 text-right">Ya existentes</th>
          <th className="py-2 pr-3 text-right">Cargados</th>
          <th className="py-2 pr-3 text-right">Pendientes</th>
          <th className="py-2">Detalle</th>
        </tr>
      </thead>
      <tbody>
        {portales.map((p) => (
          <tr key={p.portal} className="border-b border-border/60 align-top">
            <td className="py-2 pr-3 font-medium">{p.portal}</td>
            <td className={`py-2 pr-3 ${COLOR_PORTAL[p.estado] ?? ""}`}>{ETIQUETA_PORTAL[p.estado]}</td>
            <td className="py-2 pr-3 text-right">{p.nuevos}</td>
            <td className="py-2 pr-3 text-right">{p.existentes}</td>
            <td className="py-2 pr-3 text-right">{p.cargados}</td>
            <td className="py-2 pr-3 text-right">{p.pendientes}</td>
            <td className="py-2 text-xs text-ink-secondary">{p.error ?? ""}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** Botón "Descargar ahora" y avance de la ejecución (US1, FR-002/004/005). */
export function EjecucionEnCurso({ estado }: { estado: EstadoConfiguracion | undefined }) {
  const queryClient = useQueryClient();
  const [idEjecucion, setIdEjecucion] = useState<number | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  // Si al abrir la pantalla ya hay una en curso (ej. la semanal), se sigue esa.
  useEffect(() => {
    if (estado?.enCurso && idEjecucion == null) setIdEjecucion(estado.enCurso.idEjecucion);
  }, [estado?.enCurso, idEjecucion]);

  const ejecucion = useQuery({
    queryKey: ["descarga-peajes", "ejecucion", idEjecucion],
    queryFn: () => getEjecucion(idEjecucion!),
    enabled: idEjecucion != null,
    refetchInterval: (q) => (q.state.data?.estado === "en_curso" ? 2000 : false),
  });

  const enCurso = ejecucion.data?.estado === "en_curso";

  useEffect(() => {
    if (ejecucion.data && !enCurso) {
      queryClient.invalidateQueries({ queryKey: ["descarga-peajes"], exact: false });
    }
    // Solo al terminar: se refrescan historial, documentos, estado y contador.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enCurso]);

  const iniciar = useMutation({
    mutationFn: iniciarDescarga,
    onSuccess: (r) => {
      setAviso(null);
      setIdEjecucion(r.idEjecucion);
    },
    onError: async (e) => {
      if (e instanceof ApiError && e.status === 409) {
        setAviso("Ya hay una descarga en curso: se muestra su avance.");
        await queryClient.invalidateQueries({ queryKey: ["descarga-peajes", "estado"] });
      } else {
        setAviso(e instanceof Error ? e.message : "No se pudo iniciar la descarga");
      }
    },
  });

  const sinConfigurar = estado?.portales.filter((p) => !p.credenciales).map((p) => p.portal) ?? [];

  return (
    <section className="rounded-md border border-border bg-surface p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">Descarga</h2>
          <p className="text-sm text-ink-secondary">
            Baja los resúmenes y facturas nuevos de TelepeajePlus, TelePASE, CEAMSE y AUBASA y los carga en Compras
            cuando el total cierra.
          </p>
        </div>
        <SoloLectura>
          <button
            type="button"
            onClick={() => iniciar.mutate()}
            disabled={iniciar.isPending || enCurso}
            className="rounded-sm bg-finance px-4 py-2 text-sm text-white hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {enCurso ? "Descargando…" : "Descargar ahora"}
          </button>
        </SoloLectura>
      </div>
      {sinConfigurar.length > 0 && (
        <p className="mt-2 text-sm text-amber-800">
          Sin credenciales: {sinConfigurar.join(", ")}. Esos portales se van a saltear.
        </p>
      )}
      {aviso && <p className="mt-2 text-sm text-amber-800">{aviso}</p>}

      {ejecucion.data && (
        <div className="mt-4 space-y-4">
          <p className="text-sm">
            Ejecución {ejecucion.data.idEjecucion}: <strong>{ETIQUETA_EJECUCION[ejecucion.data.estado]}</strong>
            {ejecucion.data.mensaje ? ` · ${ejecucion.data.mensaje}` : ""}
          </p>
          <TablaPortales portales={ejecucion.data.portales} />
          {!enCurso && (
            <div>
              <h3 className="mb-1 text-sm font-semibold">Documentos nuevos</h3>
              <DocumentosLista documentos={ejecucion.data.documentos} vacio="Sin documentos nuevos." />
            </div>
          )}
        </div>
      )}
    </section>
  );
}
