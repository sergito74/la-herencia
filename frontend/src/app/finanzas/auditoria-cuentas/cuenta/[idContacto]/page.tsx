"use client";

import { useParams } from "next/navigation";

import { RevisionCuenta } from "@/components/auditoria-cuentas/RevisionCuenta";
import { BackLink } from "@/components/ui/BackLink";

export default function RevisionCuentaPage() {
  const params = useParams<{ idContacto: string }>();
  return (
    <main className="mx-auto max-w-none px-8 py-4">
      <BackLink href="/finanzas/auditoria-cuentas">Volver a la auditoría</BackLink>
      <div className="mt-2">
        <RevisionCuenta idContacto={Number(params.idContacto)} />
      </div>
    </main>
  );
}
