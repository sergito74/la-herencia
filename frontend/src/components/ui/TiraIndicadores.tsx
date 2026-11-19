/** Indicadores en una sola franja (Sergio 19/11/2026: los encabezados ocupaban demasiado y dejaban poco espacio de
 * trabajo). Cada indicador es etiqueta + valor + detalle en una línea; ~44 px de alto en total. */
export type Indicador = { titulo: string; valor: React.ReactNode; pie?: React.ReactNode; aviso?: boolean; activo?: boolean; onClick?: () => void };

export function TiraIndicadores({ items }: { items: Indicador[] }) {
  return (
    <div className="flex flex-wrap divide-x divide-border overflow-hidden rounded-lg border border-border bg-surface">
      {items.map((i) => {
        const contenido = (
          <>
            <span className="text-[11px] font-medium uppercase tracking-wide text-ink-muted">{i.titulo}</span>
            <span className="font-data text-base font-semibold text-ink-primary">{i.valor}</span>
            {i.pie && <span className="truncate text-xs text-ink-secondary">{i.pie}</span>}
          </>
        );
        const cls = `flex min-w-[12rem] flex-1 items-baseline gap-2 px-3 py-2 text-left ${i.aviso ? "bg-status-warning-bg/50" : ""} ${i.activo ? "ring-2 ring-inset ring-finance/40" : ""}`;
        return i.onClick
          ? <button key={i.titulo} type="button" onClick={i.onClick} className={`${cls} hover:bg-surface-sunken/60`}>{contenido}</button>
          : <div key={i.titulo} className={cls}>{contenido}</div>;
      })}
    </div>
  );
}
