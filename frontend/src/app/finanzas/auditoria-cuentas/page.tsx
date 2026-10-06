"use client";

import { ResumenCausas } from "@/components/auditoria-cuentas/ResumenCausas";
import { BackLink } from "@/components/ui/BackLink";

export default function AuditoriaCuentasPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/">Volver al inicio</BackLink>
      <h1 className="mt-2 text-2xl font-semibold">Auditoría de cuentas corrientes</h1>
      <p className="mt-1 text-sm text-ink-secondary">
        Compara cada cuenta con el saldo que tenía el Access y agrupa las diferencias por causa. Solo informa: no cambia ningún dato.
      </p>
      <div className="mt-6">
        <ResumenCausas />
      </div>
    </main>
  );
}
