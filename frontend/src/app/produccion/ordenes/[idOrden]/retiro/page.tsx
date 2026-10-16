"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams, useSearchParams } from "next/navigation";
import { Suspense, useEffect } from "react";

import { FormularioRetiroDocumento } from "@/components/ordenes/FormularioRetiroDocumento";
import { BackLink } from "@/components/ui/BackLink";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { fetchOrden, urlExportarFormularioRetiro, urlPdfFormularioRetiro } from "@/services/ordenesApi";

/** Formulario de Retiro listo para imprimir o guardar como PDF (A4 apaisado). */
function Contenido() {
  const id = Number(useParams<{ idOrden: string }>().idOrden);
  const imprimir = useSearchParams().get("imprimir") === "1";
  const { data: orden, isLoading, isError } = useQuery({ queryKey: ["orden", id], queryFn: () => fetchOrden(id), staleTime: 0 });

  useEffect(() => {
    if (imprimir && orden?.formularioRetiro) {
      const t = setTimeout(() => window.print(), 300);
      return () => clearTimeout(t);
    }
  }, [imprimir, orden]);

  if (isLoading) return <LoadingState />;
  if (isError || !orden) return <ErrorState message="No se pudo cargar la orden." />;
  if (!orden.formularioRetiro) return <p className="text-sm text-ink-secondary">La orden {id} no tiene Formulario de Retiro.</p>;
  return (
    <>
      <div className="mb-4 flex items-center justify-between print:hidden">
        <BackLink href={`/produccion/ordenes/${id}`}>Volver a la orden</BackLink>
        <div className="flex gap-2">
          <button type="button" onClick={() => window.print()} className="rounded bg-finance px-3 py-1.5 text-sm text-white hover:opacity-90">
            Imprimir
          </button>
          <a href={urlPdfFormularioRetiro(id)} className="rounded border border-border px-3 py-1.5 text-sm hover:bg-surface-sunken">
            Exportar a PDF
          </a>
          <a href={urlExportarFormularioRetiro(id)} className="rounded border border-border px-3 py-1.5 text-sm hover:bg-surface-sunken">
            Exportar a Excel
          </a>
        </div>
      </div>
      <div className="rounded border border-border shadow-sm print:border-0 print:shadow-none">
        <FormularioRetiroDocumento orden={orden} />
      </div>
    </>
  );
}

export default function FormularioRetiroPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-4 print:p-0">
      <style>{"@page { size: A4 landscape; margin: 10mm; }"}</style>
      <Suspense fallback={null}>
        <Contenido />
      </Suspense>
    </main>
  );
}
