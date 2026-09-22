"use client";

import { Suspense } from "react";
import { useParams } from "next/navigation";

import { RemitoForm } from "@/components/remitos/RemitoForm";

export default function EditarRemitoPage() {
  const params = useParams<{ idRemito: string }>();
  return (
    <main className="mx-auto max-w-6xl px-8 py-6">
      <h1 className="text-2xl font-semibold">Editar remito</h1>
      <p className="mt-2 text-xs text-ink-secondary">
        Los renglones ya consumidos o vinculados a una factura quedan congelados (producto, unidad y cantidad). Para corregirlos hay que anular el remito con un motivo y cargar uno nuevo.
      </p>
      <div className="mt-4">
        <Suspense fallback={null}>
          <RemitoForm idRemito={Number(params.idRemito)} />
        </Suspense>
      </div>
    </main>
  );
}
