"use client";

import Link from "next/link";

import { TableroColas } from "@/components/revision-cuentas/TableroColas";
import { BackLink } from "@/components/ui/BackLink";

export default function RevisionCuentasPage() {
  return (
    <main className="mx-auto max-w-none space-y-4 px-8 py-6">
      <BackLink href="/">Volver al inicio</BackLink>
      <h1 className="text-2xl font-semibold">Revisión de cuentas</h1>
      <p className="text-sm text-ink-secondary">
        Lleva cada cuenta a reflejar la realidad financiera: documentos completos, movimientos correctos, saldo respaldado por evidencia e imputaciones sanas.
        Las cuentas se agrupan por tipo de problema y se resuelven en lote. Solo Sergio aprueba los cierres.
      </p>
      <p className="text-xs">
        <Link className="text-finance underline" href="/finanzas/revision-cuentas/archivos">Archivos incompletos de comprobantes</Link>
        {" · "}
        <Link className="text-finance underline" href="/finanzas/auditoria-cuentas">Auditoría de cuentas</Link>
      </p>
      <TableroColas />
    </main>
  );
}
