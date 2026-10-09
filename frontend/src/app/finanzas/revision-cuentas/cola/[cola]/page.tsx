"use client";

import { useParams } from "next/navigation";

import { ColaCuentas } from "@/components/revision-cuentas/ColaCuentas";
import { LoteCola } from "@/components/revision-cuentas/LoteCola";
import { BackLink } from "@/components/ui/BackLink";
import type { Cola } from "@/services/revisionCuentasApi";

const COLAS = ["A", "B", "C", "D", "E", "F", "G", "H", "I"];

export default function ColaPage() {
  const params = useParams<{ cola: string }>();
  const cola = String(params.cola ?? "").toUpperCase();
  if (!COLAS.includes(cola)) {
    return (
      <main className="mx-auto max-w-none px-8 py-6">
        <BackLink href="/finanzas/revision-cuentas">Volver a la revisión de cuentas</BackLink>
        <p className="mt-4 text-sm text-status-danger">La cola no existe: usá una letra de la A a la I.</p>
      </main>
    );
  }
  return (
    <main className="mx-auto max-w-none space-y-6 px-8 py-6">
      <BackLink href="/finanzas/revision-cuentas">Volver a la revisión de cuentas</BackLink>
      <LoteCola cola={cola as Cola} />
      <ColaCuentas cola={cola as Cola} />
    </main>
  );
}
