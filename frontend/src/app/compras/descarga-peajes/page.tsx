"use client";

import { useQuery } from "@tanstack/react-query";

import { DocumentosLista } from "@/components/descarga-peajes/DocumentosLista";
import { EjecucionEnCurso } from "@/components/descarga-peajes/EjecucionEnCurso";
import { EstadoConfiguracion } from "@/components/descarga-peajes/EstadoConfiguracion";
import { Historial } from "@/components/descarga-peajes/Historial";
import { BackLink } from "@/components/ui/BackLink";
import { getDocumentos, getEstado } from "@/services/descargaPeajesApi";

/** Compras › Descarga de peajes (037): descarga y carga automática de
 * comprobantes de TelepeajePlus, TelePASE, CEAMSE y AUBASA. */
export default function DescargaPeajesPage() {
  const estado = useQuery({ queryKey: ["descarga-peajes", "estado"], queryFn: getEstado });
  const pendientes = useQuery({
    queryKey: ["descarga-peajes", "documentos", "pendiente"],
    queryFn: () => getDocumentos("pendiente"),
  });

  return (
    <main className="mx-auto max-w-none space-y-4 px-8 py-6">
      <BackLink href="/compras">Volver a Compras</BackLink>
      <h1 className="text-2xl font-semibold">Descarga de peajes</h1>
      {estado.isError && <p className="text-sm text-red-700">No se pudo leer el estado de la descarga.</p>}
      <EstadoConfiguracion estado={estado.data} />
      <EjecucionEnCurso estado={estado.data} />
      <section className="rounded-md border border-border bg-surface p-4">
        <h2 className="mb-2 text-base font-semibold">Pendientes de carga manual</h2>
        <DocumentosLista
          documentos={pendientes.data?.items ?? []}
          vacio={pendientes.isLoading ? "Cargando…" : "No hay documentos pendientes."}
        />
      </section>
      <Historial />
    </main>
  );
}
