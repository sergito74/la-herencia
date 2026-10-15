"use client";

import { Suspense } from "react";

import { RemitoForm } from "@/components/remitos/RemitoForm";
import { BackLink } from "@/components/ui/BackLink";

export default function NuevoRemitoPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-3">
      <BackLink href="/produccion/remitos">Volver a Remitos</BackLink>
      <div className="mt-2">
        <Suspense fallback={null}>
          <RemitoForm />
        </Suspense>
      </div>
    </main>
  );
}
