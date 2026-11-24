import { Suspense } from 'react';
import { OrdenesPago } from '@/components/ordenes-pago/OrdenesPago';
import { NuevosParaRevisar } from '@/components/documentos-nuevos/NuevosParaRevisar';

// 24/11/2026: los avisos del módulo pagos que no son recibos para vincular (ej. un recordatorio de débito o la
// presentación del F931) no tenían dónde verse: el número del menú llevaba acá y no aparecían.
export default function Page() {
  return (
    <Suspense fallback={<p>Cargando pagos…</p>}>
      <div className="mx-auto max-w-none px-6 pt-3"><NuevosParaRevisar modulo="pagos" /></div>
      <OrdenesPago />
    </Suspense>
  );
}
