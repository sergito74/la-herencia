import Link from "next/link";

const MODULES = [
  {
    href: "/compras",
    label: "Compras",
    description: "Buscar y listar compras, ver detalle y trazabilidad hacia cuentas corrientes.",
  },
  {
    href: "/tesoreria",
    label: "Tesorería",
    description: "Movimientos por banco, caja, valores y tarjetas. Carga y validación de resúmenes Excel.",
  },
  {
    href: "/cuentas-corrientes",
    label: "Cuentas corrientes",
    description: "Saldo y movimientos por contacto, con origen explícito hacia compras o tesorería.",
  },
];

export default function Home() {
  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-2xl font-semibold">La Herencia</h1>
      <p className="mt-2 text-slate-600">
        Sistema administrativo — migración progresiva, módulo por módulo (solo lectura).
      </p>
      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
        {MODULES.map((m) => (
          <Link
            key={m.href}
            href={m.href}
            className="rounded-lg border border-slate-200 bg-white p-4 transition hover:border-slate-400 hover:shadow-sm"
          >
            <h2 className="font-semibold text-slate-900">{m.label}</h2>
            <p className="mt-1 text-sm text-slate-600">{m.description}</p>
          </Link>
        ))}
      </div>
    </main>
  );
}
