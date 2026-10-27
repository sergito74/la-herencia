"use client";

import { useSearchParams } from "next/navigation";
import type { ReactNode } from "react";

import { NuevosParaRevisar } from "@/components/documentos-nuevos/NuevosParaRevisar";
import { RevisionComprasEnFormulario } from "@/components/documentos-nuevos/RevisionComprasEnFormulario";

/** Con `?nuevos=1` Compras muestra la revisión en el formulario de carga en lugar del listado;
 * lo "sin clasificar" (todavía sin módulo) sigue en la vista de avisos para moverlo. */
export function ComprasConRevision({ listado }: { listado: ReactNode }) {
  const params = useSearchParams();
  if (params.get("nuevos") !== "1") return <>{listado}</>;
  return (
    <div className="space-y-6">
      <RevisionComprasEnFormulario />
      <NuevosParaRevisar modulo="sin_clasificar" />
    </div>
  );
}
