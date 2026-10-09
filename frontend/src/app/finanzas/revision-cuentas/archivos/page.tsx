"use client";

import { ArchivosIncompletos } from "@/components/revision-cuentas/ArchivosIncompletos";
import { BackLink } from "@/components/ui/BackLink";

export default function ArchivosIncompletosPage() {
  return (
    <main className="mx-auto max-w-none space-y-4 px-8 py-6">
      <BackLink href="/finanzas/revision-cuentas">Volver a la revisión de cuentas</BackLink>
      <h1 className="text-2xl font-semibold">Archivos incompletos de comprobantes</h1>
      <p className="text-sm text-ink-secondary">
        Revisa las carpetas de compras y avisa de los archivos que quedaron a medio descargar o no se pueden leer, para que ninguna factura se saltee
        en silencio. Solo lee: no modifica, renombra ni borra ningún archivo.
      </p>
      <ArchivosIncompletos />
    </main>
  );
}
