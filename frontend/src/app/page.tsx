"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { KpiCard } from "@/components/ui/KpiCard";
import { fetchArrendamientos } from "@/services/arrendamientosApi";

const PRINCIPALES = [
  {
    href: "/tesoreria",
    label: "Tesorería",
    description:
      "Movimientos por banco, caja, valores y tarjetas. Carga y validación de resúmenes Excel.",
  },
  {
    href: "/cuentas-corrientes",
    label: "Cuentas corrientes",
    description:
      "Saldo y movimientos por contacto, con origen explícito hacia compras, tesorería y otros movimientos.",
  },
  {
    href: "/compras",
    label: "Compras",
    description: "Buscar y listar compras, ver detalle y trazabilidad hacia cuentas corrientes.",
  },
];

// Nota UX (consulta a 08-agro-erp-frontend-specialist, ver plan.md de
// specs/005-egresos-y-ventas-menores): dominios de bajo volumen que se
// consultan "cuando hace falta", no a diario — sección secundaria.
const OTROS_MOVIMIENTOS = [
  { href: "/impuestos", label: "Impuestos", description: "Impuestos y retenciones impositivas." },
  {
    href: "/remuneraciones",
    label: "Remuneraciones",
    description: "Liquidaciones y pagos efectivos.",
  },
  { href: "/arrendamientos", label: "Arrendamientos", description: "Contratos y cobros asociados." },
  {
    href: "/ventas-hacienda",
    label: "Ventas de hacienda",
    description: "Ventas por comprador y retenciones asociadas.",
  },
];

/**
 * KPI real (no inventado): cuotas de arrendamiento vencidas/pendientes,
 * calculado sobre datos ya expuestos por /api/arrendamientos. No hay un
 * endpoint de "saldo consolidado" en el backend hoy — no se fabrica ese
 * número aquí (design/agroux-frontend-redesign.md §5.3/§7).
 */
function CuotasArrendamientoKpis() {
  const { data } = useQuery({
    queryKey: ["home-arrendamientos-kpi"],
    queryFn: () => fetchArrendamientos({ page: 1, pageSize: 200 }),
  });

  if (!data) return null;

  const hoy = new Date().toISOString().slice(0, 10);
  let vencidas = 0;
  let pendientes = 0;
  for (const a of data.items) {
    for (const c of a.cobros) {
      if (c.estado && c.estado.toLowerCase() === "cobrado") continue;
      pendientes += 1;
      if (c.fechaVencimiento && c.fechaVencimiento < hoy) vencidas += 1;
    }
  }

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-2">
      <KpiCard label="Cuotas de arrendamiento pendientes" value={String(pendientes)} tone="warning" />
      <KpiCard
        label="Cuotas de arrendamiento vencidas"
        value={String(vencidas)}
        tone={vencidas > 0 ? "danger" : "success"}
      />
    </div>
  );
}

export default function Home() {
  return (
    <main className="mx-auto max-w-4xl p-8">
      <h1 className="text-2xl font-semibold text-ink-primary">La Herencia</h1>
      <p className="mt-2 text-ink-secondary">
        Sistema administrativo — migración progresiva, módulo por módulo (solo lectura).
      </p>

      <div className="mt-6">
        <CuotasArrendamientoKpis />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        {PRINCIPALES.map((m) => (
          <Link
            key={m.href}
            href={m.href}
            className="rounded-md border border-border bg-surface p-5 transition hover:border-border-strong hover:shadow-sm"
          >
            <h2 className="font-semibold text-ink-primary">{m.label}</h2>
            <p className="mt-1 text-sm text-ink-secondary">{m.description}</p>
          </Link>
        ))}
      </div>

      <h2 className="mt-8 text-sm font-medium uppercase tracking-wide text-ink-secondary">
        Otros movimientos
      </h2>
      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {OTROS_MOVIMIENTOS.map((m) => (
          <Link
            key={m.href}
            href={m.href}
            className="rounded-md border border-border bg-surface p-3 text-sm transition hover:border-border-strong hover:shadow-sm"
          >
            <h3 className="font-medium text-ink-primary">{m.label}</h3>
            <p className="mt-1 text-ink-secondary">{m.description}</p>
          </Link>
        ))}
      </div>
    </main>
  );
}
