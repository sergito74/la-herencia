import Link from "next/link";
import { Suspense } from "react";

import { ComprasListado } from "@/components/compras/ComprasListado";
import { LoadingState } from "@/components/ui/States";

export const metadata = {
  title: "Compras",
};

export default function ComprasPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Compras</h1>
        <Link
          href="/compras/nueva"
          className="rounded-sm bg-agro px-4 py-2 text-sm text-white hover:opacity-90"
        >
          + Nueva compra
        </Link>
      </div>
      <div className="mt-6">
        <Suspense fallback={<LoadingState />}>
          <ComprasListado />
        </Suspense>
      </div>
    </main>
  );
}
