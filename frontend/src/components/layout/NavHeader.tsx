"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/components/auth/AuthContext";

interface NavLeaf {
  href: string;
  label: string;
}

interface NavItem {
  href: string;
  label: string;
  icon: JSX.Element;
  submenu?: NavLeaf[];
  disabled?: boolean;
  disabledTitle?: string;
}

/** Íconos SVG inline — sin agregar dependencia nueva (constitución, principio
 * VII). Trazo simple 1.5px, 18x18, consistente con la densidad "administrativa"
 * del design system (design/agroux-frontend-redesign.md §2.3). */
const ICONS = {
  compras: (
    <path d="M4 6h16l-1.5 9.5a2 2 0 0 1-2 1.5H7.5a2 2 0 0 1-2-1.5L4 6Zm0 0-.5-2H2M9 10v3m6-3v3" />
  ),
  ventas: <path d="M4 18 10 12l4 4 6-7M14 8h6v6" />,
  finanzas: <path d="M12 3v18M6 7h9a3 3 0 0 1 0 6H9a3 3 0 0 0 0 6h9" />,
  personal: (
    <path d="M17 20v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2M11 4a4 4 0 1 1 0 8 4 4 0 0 1 0-8Zm8 16v-2a4 4 0 0 0-3-3.87M16 4.13A4 4 0 0 1 16 11.87" />
  ),
  produccion: <path d="M12 3 4 9v12h16V9l-8-6Zm-4 18v-6h8v6" />,
  contactos: <path d="M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM4 21v-1a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v1" />,
  bell: <path d="M6 8a6 6 0 1 1 12 0c0 4 1.5 5.5 1.5 5.5H4.5S6 12 6 8Zm4.5 9.5a1.5 1.5 0 0 0 3 0" />,
  chevron: <path d="m6 9 6 6 6-6" />,
};

function Icon({ children, className = "h-4 w-4" }: { children: JSX.Element; className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

/**
 * Estructura de navegación por proceso de negocio, no por orden de
 * construcción — ver design/erp-module-architecture.md (reemplaza en
 * autoridad la agrupación anterior de design/agroux-frontend-redesign.md).
 *
 * Polish 2026-09-16: íconos por módulo + shell bar de dos franjas — patrón
 * confirmado en SAP Fiori (shell bar superior fija con branding/búsqueda/
 * notificaciones/usuario, franja de navegación separada) y en Odoo 17+
 * (top bar con identidad de app + selector, ver design/agroux-frontend-redesign.md
 * sección "2026-09-16 — Polish de navegación" para el detalle de research).
 */
const NAV_ITEMS: NavItem[] = [
  { href: "/compras", label: "Compras", icon: ICONS.compras },
  {
    href: "/ventas/hacienda",
    label: "Ventas",
    icon: ICONS.ventas,
    submenu: [
      { href: "/ventas/hacienda", label: "Hacienda" },
      { href: "/ventas/granos", label: "Granos" },
    ],
  },
  {
    href: "/finanzas",
    label: "Finanzas",
    icon: ICONS.finanzas,
    submenu: [
      { href: "/finanzas/tesoreria", label: "Tesorería" },
      { href: "/finanzas/cuentas-corrientes", label: "Cuentas corrientes" },
      { href: "/finanzas/tarjetas", label: "Tarjetas" },
      { href: "/finanzas/impuestos", label: "Impuestos y retenciones" },
      { href: "/finanzas/arrendamientos", label: "Arrendamientos" },
    ],
  },
  {
    href: "/personal",
    label: "Personal",
    icon: ICONS.personal,
    submenu: [{ href: "/personal/remuneraciones", label: "Remuneraciones" }],
  },
  {
    href: "/produccion",
    label: "Producción",
    icon: ICONS.produccion,
    submenu: [
      { href: "/produccion/planificacion", label: "Planificación agrícola" },
      { href: "/produccion/remitos", label: "Remitos" },
      { href: "/produccion/stock", label: "Existencias de insumos" },
      { href: "/produccion/stock/bajas", label: "Bajas de stock" },
      { href: "/produccion/stock/ajustes", label: "Ajustes de inventario" },
      { href: "/produccion/ordenes", label: "Órdenes de trabajo" },
      { href: "/produccion/resultado-cultivo", label: "Resultado de cultivo" },
    ],
  },
  {
    href: "/contactos",
    label: "Contactos",
    icon: ICONS.contactos,
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
        className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors ${
          active
            ? "bg-finance-light font-medium text-finance"
            : "text-ink-secondary hover:bg-surface-sunken hover:text-ink-primary"
        }`}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <Icon>{item.icon}</Icon>
        {item.label}
        <Icon className={`h-3.5 w-3.5 transition-transform ${open ? "rotate-180" : ""}`}>{ICONS.chevron}</Icon>
      </button>
      {open && (
        <div className="absolute left-0 top-full z-10 min-w-[14rem] origin-top-left rounded-md border border-border bg-surface py-1 shadow-lg ring-1 ring-black/5 animate-[fadeIn_0.1s_ease-out]">
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
  const router = useRouter();
  const { usuario, logout } = useAuth();

  if (pathname === "/login") return null;

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-surface shadow-sm">
      {/* Una sola franja: logo + navegación por proceso de negocio a la
          izquierda, selector de contexto/notificaciones/usuario a la
          derecha — todo en la misma línea para no gastar alto de más
          (pedido explícito del usuario, 2026-09-17). */}
      <div className="flex w-full items-center justify-between gap-4 px-8 py-2">
        <div className="flex min-w-0 items-center gap-4">
          <Link href="/" className="flex shrink-0 items-center gap-2 font-semibold text-ink-primary">
            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-agro text-sm text-white">
              LH
            </span>
            La Herencia
          </Link>
          <div className="flex items-center gap-1">
            {NAV_ITEMS.map((item) => {
              if (item.disabled) {
                return (
                  <span
                    key={item.href}
                    title={item.disabledTitle}
                    className="flex cursor-not-allowed items-center gap-2 rounded-md px-3 py-2 text-sm text-ink-muted"
                  >
                    <Icon>{item.icon}</Icon>
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
                  className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                    active
                      ? "bg-finance-light text-finance"
                      : "text-ink-secondary hover:bg-surface-sunken hover:text-ink-primary"
                  }`}
                >
                  <Icon>{item.icon}</Icon>
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-3">
          <button
            type="button"
            disabled
            title="Selector de Establecimiento/Campaña — próximamente"
            className="rounded-sm border border-border px-3 py-1 text-xs text-ink-muted disabled:cursor-not-allowed"
          >
            Establecimiento: todos
          </button>
          <button
            type="button"
            disabled
            title="Notificaciones — próximamente"
            className="rounded-full p-1.5 text-ink-muted hover:bg-surface-sunken disabled:cursor-not-allowed disabled:hover:bg-transparent"
          >
            <Icon>{ICONS.bell}</Icon>
          </button>
          {usuario && (
            <div className="flex items-center gap-2">
              <span
                title={`${usuario.nombre ?? usuario.usuario} (${usuario.rol})`}
                className="text-sm text-ink-secondary"
              >
                {usuario.nombre ?? usuario.usuario}
              </span>
              <button
                type="button"
                onClick={handleLogout}
                title="Cerrar sesión"
                className="rounded-md border border-border px-3 py-1 text-xs text-ink-secondary hover:bg-surface-sunken"
              >
                Cerrar sesión
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
