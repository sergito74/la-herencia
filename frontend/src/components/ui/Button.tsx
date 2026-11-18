import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";

/** Botón del sistema (design/agroux-frontend-redesign.md, regla 18/11/2026):
 * - primary: la acción principal de la pantalla, siempre azul finanzas (una por zona);
 * - secondary: acciones comunes, con borde;
 * - ghost: acciones de bajo peso dentro de tablas o tarjetas;
 * - danger: acciones que borran o anulan.
 * Los acentos agro/ganadería son solo para etiquetas, no para botones. */
export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md";

const BASE = "inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-md font-medium transition-colors " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-finance/40 disabled:cursor-not-allowed disabled:opacity-60";
const VARIANTES: Record<ButtonVariant, string> = {
  primary: "bg-finance text-white shadow-sm hover:bg-finance/90",
  secondary: "border border-border bg-surface text-ink-primary hover:bg-surface-sunken",
  ghost: "text-finance hover:bg-finance-light",
  danger: "border border-status-danger/40 bg-surface text-status-danger hover:bg-status-danger-bg",
};
const TAMANIOS: Record<ButtonSize, string> = { sm: "px-2.5 py-1 text-xs", md: "px-3.5 py-2 text-sm" };

export function buttonClass(variant: ButtonVariant = "secondary", size: ButtonSize = "md", extra = ""): string {
  return `${BASE} ${VARIANTES[variant]} ${TAMANIOS[size]} ${extra}`.trim();
}

export function Button({ variant = "secondary", size = "md", className = "", type = "button", ...rest }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; size?: ButtonSize }) {
  return <button type={type} className={buttonClass(variant, size, className)} {...rest} />;
}

export function ButtonLink({ href, variant = "secondary", size = "md", className = "", children }:
  { href: string; variant?: ButtonVariant; size?: ButtonSize; className?: string; children: ReactNode }) {
  return <Link href={href} className={buttonClass(variant, size, className)}>{children}</Link>;
}
