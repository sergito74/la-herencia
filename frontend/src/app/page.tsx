import Link from "next/link";

const PRINCIPALES = [
  {
    href: "/tesoreria",
    label: "Tesorería",
    description: "Movimientos por banco, caja, valores y tarjetas. Carga y validación de resúmenes Excel.",
  },
  {
    href: "/cuentas-corrientes",
    label: "Cuentas corrientes",
    description: "Saldo y movimientos por contacto, con origen explícito hacia compras, tesorería y otros movimientos.",
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
  {
    href: "/impuestos",
    label: "Impuestos",
    description: "Impuestos y retenciones impositivas.",
  },
  {
    href: "/remuneraciones",
    label: "Remuneraciones",
    description: "Liquidaciones y pagos efectivos.",
  },
  {
    href: "/arrendamientos",
    label: "Arrendamientos",
    description: "Contratos y cobros asociados.",
  },
  {
    href: "/ventas-hacienda",
    label: "Ventas de hacienda",
    description: "Ventas por comprador y retenciones asociadas.",
  },
];

export default function Home() {
  return (
    <main className="mx-auto max-w-4xl p-8">
      <h1 className="text-2xl font-semibold">La Herencia</h1>
      <p className="mt-2 text-slate-600">
        Sistema administrativo — migración progresiva, módulo por módulo (solo lectura).
      </p>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        {PRINCIPALES.map((m) => (
          <Link
            key={m.href}
            href={m.href}
            className="rounded-lg border border-slate-200 bg-white p-5 transition hover:border-slate-400 hover:shadow-sm"
          >
            <h2 className="font-semibold text-slate-900">{m.label}</h2>
            <p className="mt-1 text-sm text-slate-600">{m.description}</p>
          </Link>
        ))}
      </div>

      <h2 className="mt-8 text-sm font-medium uppercase tracking-wide text-slate-500">
        Otros movimientos
      </h2>
      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {OTROS_MOVIMIENTOS.map((m) => (
          <Link
            key={m.href}
            href={m.href}
            className="rounded-lg border border-slate-200 bg-white p-3 text-sm transition hover:border-slate-400 hover:shadow-sm"
          >
            <h3 className="font-medium text-slate-900">{m.label}</h3>
            <p className="mt-1 text-slate-600">{m.description}</p>
          </Link>
        ))}
      </div>
    </main>
  );
}
