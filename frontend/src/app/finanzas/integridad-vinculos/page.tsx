"use client";

import { ControlIntegridad } from "@/components/integridad/ControlIntegridad";
import { RevisionLote } from "@/components/integridad/RevisionLote";

export default function IntegridadVinculosPage() {
  return (
    <main className="mx-auto max-w-none space-y-8 px-8 py-6">
      <section>
        <h1 className="text-2xl font-semibold">Integridad de vínculos</h1>
        <p className="mt-1 text-sm text-ink-secondary">
          Controla que cada pago esté vinculado a sus documentos una sola vez, sin importar desde qué pantalla se
          vinculó (aplicaciones, tarjetas, cheques, tesorería). Clic en una categoría para filtrar.
        </p>
        <div className="mt-4">
          <ControlIntegridad />
        </div>
      </section>
      <section>
        <h2 className="text-xl font-semibold">Corrección por lotes</h2>
        <p className="mt-1 text-sm text-ink-secondary">
          La propuesta agrupa por motivo y certeza. Nada se borra: las aplicaciones erróneas se anulan con motivo, se
          toma un backup verificado antes de aplicar y cada lote se puede revertir. Las aplicaciones manuales nunca se
          tocan.
        </p>
        <div className="mt-4">
          <RevisionLote />
        </div>
      </section>
    </main>
  );
}
