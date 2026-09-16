"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const MODULES = [
  { href: "/compras", label: "Compras" },
  { href: "/tesoreria", label: "Tesorería" },
  { href: "/cuentas-corrientes", label: "Cuentas corrientes" },
];

export function NavHeader() {
  const pathname = usePathname();

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center gap-6 px-8 py-3">
        <Link href="/" className="font-semibold text-slate-900">
          La Herencia
        </Link>
        <nav className="flex gap-4 text-sm">
          {MODULES.map((m) => {
            const active = pathname === m.href || pathname.startsWith(`${m.href}/`);
            return (
              <Link
                key={m.href}
                href={m.href}
                className={
                  active
                    ? "font-medium text-slate-900 underline underline-offset-4"
                    : "text-slate-600 hover:text-slate-900"
                }
              >
                {m.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
