import Link from 'next/link';
import { BackfillDiagnostico } from '@/components/impuestos/BackfillDiagnostico';
export default function BackfillPage(){return <main className="mx-auto max-w-none space-y-6 px-8 py-6"><Link href="/finanzas/impuestos">Volver a Impuestos</Link><h1 className="text-2xl font-semibold">Completar boletas faltantes</h1><p>Revisá los pagos y sus respaldos antes de cargar nuevas boletas.</p><BackfillDiagnostico/></main>;}
