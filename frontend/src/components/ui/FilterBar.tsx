/**
 * Contenedor estandarizado para los formularios de filtro repetidos en
 * cada módulo (design/agroux-frontend-redesign.md §4.6). Reemplaza el
 * `<form className="flex gap-2 rounded-lg border ...">` copiado a mano en
 * cada componente de listado.
 */
export function FilterBar({
  onSubmit,
  children,
}: {
  onSubmit: (e: React.FormEvent) => void;
  children: React.ReactNode;
}) {
  return (
    <form
      onSubmit={onSubmit}
      className="flex flex-wrap items-end gap-3 rounded-md border border-border bg-surface p-4"
    >
      {children}
    </form>
  );
}

export function FilterField({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-1 min-w-[10rem] flex-col gap-1 text-sm text-ink-secondary">
      {label}
      {children}
    </label>
  );
}

export const filterInputClass =
  "rounded-sm border border-border px-2 py-1 text-ink-primary focus:border-border-strong focus:outline-none";

export function FilterSubmitButton({ children = "Buscar" }: { children?: React.ReactNode }) {
  return (
    <button
      type="submit"
      className="rounded-sm bg-finance px-4 py-2 text-sm text-white hover:opacity-90"
    >
      {children}
    </button>
  );
}
