"use client";

import { useRef } from "react";

/**
 * Pestañas accesibles (role tablist/tab/tabpanel, flechas ← → / Inicio / Fin).
 * La pestaña activa la controla quien la usa (ej. sincronizada con `?tab=`).
 */
export function Tabs<T extends string>({
  tabs,
  activa,
  onChange,
  idBase,
  children,
}: {
  tabs: { id: T; label: string; aviso?: number }[];
  activa: T;
  onChange: (id: T) => void;
  idBase: string;
  children: React.ReactNode;
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const mover = (i: number) => {
    const n = (i + tabs.length) % tabs.length;
    onChange(tabs[n].id);
    refs.current[n]?.focus();
  };
  const actual = tabs.findIndex((t) => t.id === activa);
  return (
    <div>
      <div role="tablist" aria-label="Secciones" className="flex gap-1 border-b border-border">
        {tabs.map((t, i) => (
          <button
            key={t.id}
            ref={(el) => {
              refs.current[i] = el;
            }}
            role="tab"
            id={`${idBase}-tab-${t.id}`}
            aria-selected={t.id === activa}
            aria-controls={`${idBase}-panel`}
            tabIndex={t.id === activa ? 0 : -1}
            onClick={() => onChange(t.id)}
            onKeyDown={(e) => {
              if (e.key === "ArrowRight") mover(actual + 1);
              else if (e.key === "ArrowLeft") mover(actual - 1);
              else if (e.key === "Home") mover(0);
              else if (e.key === "End") mover(tabs.length - 1);
              else return;
              e.preventDefault();
            }}
            className={`-mb-px border-b-2 px-4 py-2 text-sm ${
              t.id === activa ? "border-agro font-semibold text-ink-primary" : "border-transparent text-ink-secondary hover:text-ink-primary"
            }`}
          >
            {t.label}
            {t.aviso ? (
              <span className="ml-2 rounded-sm bg-status-warning-bg px-1.5 text-xs text-status-warning" aria-label={`${t.aviso} alertas`}>
                {t.aviso}
              </span>
            ) : null}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`${idBase}-panel`} aria-labelledby={`${idBase}-tab-${activa}`} className="pt-5">
        {children}
      </div>
    </div>
  );
}
