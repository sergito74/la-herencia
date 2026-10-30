import { Suspense } from 'react';
import { OrdenesPago } from '@/components/ordenes-pago/OrdenesPago';
export default function Page(){return <Suspense fallback={<p>Cargando pagos…</p>}><OrdenesPago/></Suspense>;}
