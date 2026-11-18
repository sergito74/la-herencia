/** Sección de formulario (18/11/2026): tarjeta con título y ayuda opcional. Reemplaza los títulos sueltos en
 * mayúsculas grises; cada bloque del formulario queda agrupado y separado del siguiente. */
export function FormSection({ titulo, ayuda, acciones, children, className = "" }: {
  titulo: React.ReactNode;
  ayuda?: React.ReactNode;
  acciones?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-lg border border-border bg-surface p-4 shadow-sm ${className}`}>
      <header className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-ink-primary">{titulo}</h2>
          {ayuda && <p className="text-xs text-ink-secondary">{ayuda}</p>}
        </div>
        {acciones && <div className="flex items-center gap-2">{acciones}</div>}
      </header>
      {children}
    </section>
  );
}

/** Clase común de campos de formulario (input/select/textarea). */
export const campoClass =
  "mt-1 w-full rounded-md border border-border bg-surface px-2.5 py-1.5 text-sm text-ink-primary focus:border-finance focus:outline-none focus:ring-2 focus:ring-finance/20";
