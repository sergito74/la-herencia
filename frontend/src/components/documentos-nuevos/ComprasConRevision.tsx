"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import type { ReactNode } from "react";

import { AvisoNuevosPendientes, NuevosParaRevisar } from "@/components/documentos-nuevos/NuevosParaRevisar";
import { RevisionComprasEnFormulario } from "@/components/documentos-nuevos/RevisionComprasEnFormulario";

/** Con `?nuevos=1` Compras muestra la revisión en el formulario de carga en lugar del listado;
 * lo "sin clasificar" (todavía sin módulo) sigue en la vista de avisos para moverlo. */
export function ComprasConRevision({ listado }: { listado: ReactNode }) {
  const params = useSearchParams();
  if (params.get("nuevos") !== "1") return <><AvisoNuevosPendientes modulos={["compras", "sin_clasificar"]} />{listado}</>;
  return (
    <div className="space-y-6">
      <Link href="/compras" className="text-sm text-finance hover:underline">← Ir al listado de compras</Link>
      <RevisionComprasEnFormulario />
      <NuevosParaRevisar modulo="sin_clasificar" />
    </div>
  );
}
