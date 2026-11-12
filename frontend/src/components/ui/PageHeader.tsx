import Link from "next/link";

/**
 * Encabezado compacto de pantalla (12/11/2026): una sola línea con volver (flecha), título, ayuda opcional (ícono "?"
 * con la explicación al pasar el mouse) y acciones a la derecha. Reemplaza BackLink + h1 grande + párrafo explicativo.
 */
export function PageHeader({ titulo, volver, ayuda, children }: {
  titulo: React.ReactNode;
  volver?: string;
  ayuda?: string;
  children?: React.ReactNode;
}) {
  return (
    <header className="mb-3 flex min-h-[2.25rem] flex-wrap items-center gap-x-3 gap-y-2">
      {volver && (
        <Link href={volver} aria-label="Volver" title="Volver"
          className="flex h-7 w-7 items-center justify-center rounded-md text-ink-secondary hover:bg-surface-sunken hover:text-ink-primary">
          ←
        </Link>
      )}
      <h1 className="text-lg font-semibold leading-tight">{titulo}</h1>
      {ayuda && (
        <span tabIndex={0} title={ayuda} aria-label={ayuda}
          className="flex h-5 w-5 cursor-help items-center justify-center rounded-full border border-border text-[11px] text-ink-secondary">
          ?
        </span>
      )}
      {children && <div className="ml-auto flex flex-wrap items-center gap-2">{children}</div>}
    </header>
  );
}
