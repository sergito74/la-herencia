"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

interface NavLeaf {
  href: string;
  label: string;
}

interface NavItem {
  href: string;
  label: string;
  submenu?: NavLeaf[];
  disabled?: boolean;
  disabledTitle?: string;
}

/**
 * Estructura de navegación por proceso de negocio, no por orden de
 * construcción — ver design/erp-module-architecture.md (reemplaza en
 * autoridad la agrupación anterior de design/agroux-frontend-redesign.md).
 */
const NAV_ITEMS: NavItem[] = [
  { href: "/compras", label: "Compras" },
  { href: "/ventas/hacienda", label: "Ventas" },
  {
    href: "/finanzas",
    label: "Finanzas",
    submenu: [
      { href: "/finanzas/tesoreria", label: "Tesorería" },
      { href: "/finanzas/cuentas-corrientes", label: "Cuentas corrientes" },
      { href: "/finanzas/impuestos", label: "Impuestos y retenciones" },
      { href: "/finanzas/arrendamientos", label: "Arrendamientos" },
    ],
  },
  {
    href: "/personal",
    label: "Personal",
    submenu: [{ href: "/personal/remuneraciones", label: "Remuneraciones" }],
  },
  {
    href: "/produccion",
    label: "Producción",
    disabled: true,
    disabledTitle: "Próximamente — Órdenes de trabajo, cultivos y ganadería",
  },
];

function isActive(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(`${href}/`);
}

function NavDropdown({ item, active }: { item: NavItem; active: boolean }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <div className="relative" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <button
        type="button"
        className={`px-3 py-2.5 text-sm transition-colors ${
          active
            ? "border-b-2 border-finance bg-finance-light font-medium text-finance"
            : "border-b-2 border-transparent text-ink-secondary hover:text-ink-primary"
        }`}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        {item.label} ▾
      </button>
      {open && (
        <div className="absolute left-0 top-full z-10 min-w-[14rem] rounded-md border border-border bg-surface py-1 shadow-lg">
          {item.submenu!.map((leaf) => {
            const leafActive = isActive(pathname, leaf.href);
            return (
              <Link
                key={leaf.href}
                href={leaf.href}
                className={`block px-4 py-2 text-sm ${
                  leafActive
                    ? "font-medium text-finance"
                    : "text-ink-secondary hover:bg-surface-sunken hover:text-ink-primary"
                }`}
              >
                {leaf.label}
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function NavHeader() {
  const pathname = usePathname();

  return (
    <header className="border-b border-border bg-surface">
      {/* Franja superior: logo + slot reservado para el futuro selector de
          contexto (Establecimiento/Campaña) — no hay datos de esa
          jerarquía en SQL Server todavía. */}
      <div className="mx-auto flex max-w-6xl items-center justify-between px-8 py-2">
        <Link href="/" className="font-semibold text-ink-primary">
          La Herencia
        </Link>
        <button
          type="button"
          disabled
          title="Selector de Establecimiento/Campaña — próximamente"
          className="rounded-sm border border-border px-3 py-1 text-xs text-ink-muted disabled:cursor-not-allowed"
        >
          Establecimiento: todos
        </button>
      </div>

      {/* Franja de navegación por proceso de negocio. */}
      <div className="mx-auto flex max-w-6xl items-center gap-1 border-t border-border px-8">
        {NAV_ITEMS.map((item) => {
          if (item.disabled) {
            return (
              <span
                key={item.href}
                title={item.disabledTitle}
                className="cursor-not-allowed px-3 py-2.5 text-sm text-ink-muted"
              >
                {item.label}
              </span>
            );
          }

          const active =
            isActive(pathname, item.href) ||
            (item.submenu?.some((leaf) => isActive(pathname, leaf.href)) ?? false);

          if (item.submenu) {
            return <NavDropdown key={item.href} item={item} active={active} />;
          }

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`px-3 py-2.5 text-sm font-medium transition-colors ${
                active
                  ? "border-b-2 border-finance bg-finance-light text-finance"
                  : "border-b-2 border-transparent text-ink-secondary hover:text-ink-primary"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </div>
    </header>
  );
}
