"use client";

import { RemitosSubNav } from "@/components/remitos/RemitosSubNav";
import { FormularioCostos } from "@/components/resultado-cultivo/FormularioCostos";
import { PageHeader } from "@/components/ui/PageHeader";

/** Costos por cultivo / campaña: formato y cálculos del formulario FrmCostos de Access. */
export default function CostoCultivoPage() {
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Imputación de costos · costo por cultivo / campaña"
        ayuda="Igual que el formulario Costos de Access: costos directos por concepto, en pesos y dólares, totales y por hectárea. Clic en un concepto para ver sus comprobantes." />
      <RemitosSubNav grupo="costos" />
      <div className="mt-3"><FormularioCostos /></div>
    </main>
  );
}
