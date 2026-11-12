import { CotizacionesPanel } from "@/components/finanzas/CotizacionesPanel";

export const metadata = {
  title: "Cotizaciones (Dólar BNA / INMAG) — La Herencia",
};

export default function CotizacionesPage() {
  return <main className="mx-auto max-w-none px-6 py-3"><CotizacionesPanel /></main>;
}

