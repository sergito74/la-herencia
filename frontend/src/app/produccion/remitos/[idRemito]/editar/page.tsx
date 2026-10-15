"use client";

import { Suspense } from "react";
import { useParams } from "next/navigation";

import { RemitoForm } from "@/components/remitos/RemitoForm";
import { BackLink } from "@/components/ui/BackLink";

export default function EditarRemitoPage() {
  const params = useParams<{ idRemito: string }>();
  return (
    <main className="mx-auto max-w-none px-8 py-3">
      <BackLink href={`/produccion/remitos/${params.idRemito}`}>Volver al remito</BackLink>
      <div className="mt-2">
        <Suspense fallback={null}>
          <RemitoForm idRemito={Number(params.idRemito)} />
        </Suspense>
      </div>
    </main>
  );
}
