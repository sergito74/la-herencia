"use client";

import { FlujoCajaRubro } from "@/components/flujo-caja/FlujoCajaRubro";

export default function FlujoCajaRubroPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <h1 className="text-2xl font-semibold">Flujo de caja por rubro</h1>
      <p className="mt-1 text-sm text-ink-secondary">
        Movimientos bancarios reales (BNA + Galicia) agrupados por rubro y centro de costo, con el formato del Cash
        Flow. Clic en un importe para ver los movimientos que lo componen.
      </p>
      <div className="mt-6">
        <FlujoCajaRubro />
      </div>
    </main>
  );
}
