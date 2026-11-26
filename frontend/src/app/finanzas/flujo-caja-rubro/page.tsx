"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { PageHeader } from "@/components/ui/PageHeader";
import { FlujoCajaRubro } from "@/components/flujo-caja/FlujoCajaRubro";

export default function FlujoCajaRubroPage() {
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Flujo de caja por rubro" ayuda="Movimientos bancarios reales (BNA + Galicia + Cajas en Efectivo) agrupados por rubro y centro de costo, con el formato del Cash Flow. Clic en un importe para ver los movimientos que lo componen." />
      <div>
        <Suspense><ConCentro /></Suspense>
      </div>
    </main>
  );
}

function ConCentro() {
  const centro = useSearchParams().get("centro") ?? undefined;
  return <FlujoCajaRubro key={centro ?? "todos"} centroCosto={centro} />;
}
