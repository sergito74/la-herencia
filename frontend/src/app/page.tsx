"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { KpiCard } from "@/components/ui/KpiCard";
import { fetchArrendamientos } from "@/services/arrendamientosApi";
import { DeudaTotalKpi } from "@/components/inicio/DeudaTotalKpi";
import { TarjetasPendientesKpi } from "@/components/inicio/TarjetasPendientesKpi";
import { ResultadoCampaniaKpi } from "@/components/inicio/ResultadoCampaniaKpi";

interface ProcessCardLink {
  href: string;
  label: string;
}

interface ProcessCard {
  label: string;
  description: string;
  href?: string;
  links?: ProcessCardLink[];
}

/**
 * 5 procesos de negocio (Compras, Ventas, Finanzas, Personal, Producción),
 * todos con contenido real — ver design/erp-module-architecture.md §4.3.
 * Producción se actualizó en 015-inicio-kpis: ya no es un placeholder de
 * "próximamente", refleja los módulos migrados en 010/011/012.
 */
const PROCESOS: ProcessCard[] = [
  {
    label: "Compras",
    href: "/compras",
    description: "Compras a proveedores, con imputación por rubro/centro de costo/destino/campaña.",
  },
  {
    label: "Ventas",
    href: "/ventas/hacienda",
    description: "Ventas de hacienda por comprador, con retenciones asociadas.",
  },
  {
    label: "Finanzas",
    description: "Tesorería, cuentas corrientes, tarjetas, impuestos y arrendamientos.",
    links: [
      { href: "/finanzas/tesoreria", label: "Tesorería" },
      { href: "/finanzas/cuentas-corrientes", label: "Cuentas corrientes" },
      { href: "/finanzas/tarjetas", label: "Tarjetas" },
      { href: "/finanzas/impuestos", label: "Impuestos y retenciones" },
      { href: "/finanzas/arrendamientos", label: "Arrendamientos" },
    ],
  },
  {
    label: "Personal",
    description: "Liquidaciones de remuneraciones y pagos efectivos.",
    links: [{ href: "/personal/remuneraciones", label: "Remuneraciones" }],
  },
  {
    label: "Producción",
    description: "Planificación agrícola, remitos, stock, órdenes de trabajo y resultado de cultivo.",
    links: [
      { href: "/produccion/planificacion", label: "Planificación agrícola" },
      { href: "/produccion/remitos", label: "Remitos" },
      { href: "/produccion/stock", label: "Existencias de insumos" },
      { href: "/produccion/ordenes", label: "Órdenes de trabajo" },
      { href: "/produccion/resultado-cultivo", label: "Resultado de cultivo" },
    ],
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

function ProcessCardView({ proceso }: { proceso: ProcessCard }) {
  const content = (
    <>
      <h2 className="font-semibold text-ink-primary">{proceso.label}</h2>
      <p className="mt-1 text-sm text-ink-secondary">{proceso.description}</p>
      {proceso.links && (
        <ul className="mt-3 space-y-1 border-t border-border pt-3">
          {proceso.links.map((l) => (
            <li key={l.href}>
              <Link href={l.href} className="text-sm text-finance hover:underline">
                {l.label} →
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );

  if (proceso.href) {
    return (
      <Link
        href={proceso.href}
        className="rounded-md border border-border bg-surface p-5 transition hover:border-border-strong hover:shadow-sm"
      >
        {content}
      </Link>
    );
  }

  return <div className="rounded-md border border-border bg-surface p-5">{content}</div>;
}

export default function Home() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <h1 className="text-2xl font-semibold text-ink-primary">La Herencia</h1>
      <p className="mt-2 text-ink-secondary">
        Sistema administrativo por proceso de negocio (solo lectura salvo donde se indique).
      </p>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <DeudaTotalKpi />
        <TarjetasPendientesKpi />
        <CuotasArrendamientoKpis />
      </div>

      <div className="mt-4">
        <ResultadoCampaniaKpi />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {PROCESOS.map((p) => (
          <ProcessCardView key={p.label} proceso={p} />
        ))}
      </div>
    </main>
  );
}
