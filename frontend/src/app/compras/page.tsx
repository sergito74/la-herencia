import { PageHeader } from "@/components/ui/PageHeader";
import Link from "next/link";
import { Suspense } from "react";

import { ComprasListado } from "@/components/compras/ComprasListado";
import { LoadingState } from "@/components/ui/States";
import { ComprasConRevision } from "@/components/documentos-nuevos/ComprasConRevision";
import { SoloLectura } from "@/components/auth/SoloLectura";

export const metadata = {
  title: "Compras",
};

export default function ComprasPage() {
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Compras">
        <SoloLectura>
          <Link
            href="/compras/nueva"
            className="rounded-md bg-finance font-medium text-white shadow-sm transition-colors hover:bg-finance/90 disabled:opacity-60 px-3 py-1 text-sm hover:opacity-90"
          >
            + Nueva compra
          </Link>
        </SoloLectura>
      </PageHeader>
      <div>
        <Suspense fallback={<LoadingState />}>
          <ComprasConRevision listado={<ComprasListado />} />
        </Suspense>
      </div>
    </main>
  );
}
