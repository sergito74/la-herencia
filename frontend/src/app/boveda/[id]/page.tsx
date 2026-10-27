"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/components/auth/AuthContext";
import { AutorizacionPanel } from "@/components/boveda/AutorizacionPanel";
import { CorridasTabla } from "@/components/boveda/CorridasTabla";
import { CredencialPanel } from "@/components/boveda/CredencialPanel";
import { DocumentosTabla } from "@/components/boveda/DocumentosTabla";
import { EstadoCuentaPanel } from "@/components/boveda/EstadoCuentaPanel";
import { PortalForm } from "@/components/boveda/PortalForm";
import { ProgramacionPanel } from "@/components/boveda/ProgramacionPanel";
import { BackLink } from "@/components/ui/BackLink";
import {
  crearCredencial, editarPortal, getCorridas, getDocumentos, getPortal, type PortalEntrada,
} from "@/services/bovedaApi";

function Seccion({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <section className="rounded-md border border-border bg-surface p-4">
      <h2 className="mb-2 text-base font-semibold">{titulo}</h2>
      {children}
    </section>
  );
}

/** Detalle de un portal de la bóveda (042). */
export default function PortalPage() {
  const { id } = useParams<{ id: string }>();
  const idPortal = Number(id);
  const { usuario } = useAuth();
  const esAdmin = usuario?.rol === "Administrador";
  const qc = useQueryClient();
  const portal = useQuery({
    queryKey: ["boveda", "portal", idPortal],
    queryFn: () => getPortal(idPortal),
    enabled: esAdmin,
    // Mientras corre, se actualiza cada 2 s; al terminar refresca corridas y documentos.
    refetchInterval: (q) => (q.state.data?.enCurso || q.state.data?.enCola ? 1500 : false),
  });
  const enCurso = portal.data?.enCurso ?? false;
  const corridas = useQuery({
    queryKey: ["boveda", "corridas", idPortal, enCurso],
    queryFn: () => getCorridas(idPortal, 20),
    enabled: esAdmin,
  });
  const documentos = useQuery({
    queryKey: ["boveda", "documentos", idPortal, enCurso],
    queryFn: () => getDocumentos(idPortal, undefined, 50),
    enabled: esAdmin,
  });
  const [editando, setEditando] = useState(false);
  const guardar = useMutation({
    mutationFn: async (body: PortalEntrada) => {
      let idCredencial = body.idCredencial;
      if (body.credencialNueva) idCredencial = (await crearCredencial(body.credencialNueva)).idCredencial;
      const { credencialNueva: _, ...resto } = body;
      return editarPortal(idPortal, { ...resto, idCredencial });
    },
    onSuccess: () => { setEditando(false); qc.invalidateQueries({ queryKey: ["boveda"] }); },
  });

  if (usuario && !esAdmin) {
    return <main className="px-8 py-6 text-sm text-ink-secondary">Solo el administrador accede a la bóveda de portales.</main>;
  }
  const p = portal.data;

  return (
    <main className="mx-auto max-w-none space-y-4 px-8 py-6">
      <BackLink href="/boveda">Volver a la bóveda</BackLink>
      {portal.isError && <p className="text-sm text-red-700">{portal.error.message}</p>}
      {p && (
        <>
          <section className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-semibold">{p.nombre}</h1>
              <p className="text-sm text-ink-secondary">
                {p.tipo}{p.contacto && ` · ${p.contacto}`} ·{" "}
                {p.conector.disponible ? `Sincronización automática: ${p.conector.nombre}` : "Sincronización automática: próximamente"}
              </p>
              {p.notas && <p className="mt-1 whitespace-pre-line text-sm">{p.notas}</p>}
            </div>
            <div className="flex shrink-0 gap-2">
              <a href={p.url} target="_blank" rel="noopener noreferrer"
                className="rounded-md border border-border px-3 py-1.5 text-sm">Abrir portal</a>
              {!editando && (
                <button type="button" onClick={() => { guardar.reset(); setEditando(true); }}
                  className="rounded-md border border-border px-3 py-1.5 text-sm">Editar</button>
              )}
            </div>
          </section>
          {editando && (
            <PortalForm edicion enviando={guardar.isPending} error={guardar.error?.message ?? null}
              inicial={{ ...p, idCredencial: p.credencial?.idCredencial ?? null, codigoConector: p.conector.codigo }}
              onSubmit={(body) => guardar.mutate(body)} onCancel={() => setEditando(false)} />
          )}
          <Seccion titulo="Credencial"><CredencialPanel portal={p} /></Seccion>
          <Seccion titulo="Autorización"><AutorizacionPanel portal={p} /></Seccion>
          <Seccion titulo="Sincronización"><ProgramacionPanel portal={p} /></Seccion>
          {(p.conector.estadoCuenta || p.ultimaFoto) && (
            <Seccion titulo="Estado de cuenta"><EstadoCuentaPanel idPortal={p.idPortal} /></Seccion>
          )}
          <Seccion titulo="Documentos bajados">
            <DocumentosTabla documentos={documentos.data?.items ?? []}
              vacio={documentos.isLoading ? "Cargando…" : "Todavía no se bajaron documentos."} />
          </Seccion>
          <Seccion titulo="Corridas"><CorridasTabla corridas={corridas.data?.items ?? []} /></Seccion>
        </>
      )}
    </main>
  );
}
