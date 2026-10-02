"use client";

import { RecalculoFifo } from "@/components/recalculo-fifo/RecalculoFifo";

export default function RecalculoFifoPage() {
  return (
    <main className="mx-auto max-w-none space-y-4 px-8 py-6">
      <section>
        <h1 className="text-2xl font-semibold">Recálculo FIFO de cuentas corrientes</h1>
        <p className="mt-1 text-sm text-ink-secondary">
          Cada pago o cobro cubre el documento que vence primero. Las cadenas de tarjeta y cheque, y las elecciones
          manuales, se respetan. Las compras y ventas del mismo contacto se compensan antes que el dinero. Clic en un
          contacto para ver su cuenta renglón por renglón.
        </p>
      </section>
      <RecalculoFifo />
    </main>
  );
}
