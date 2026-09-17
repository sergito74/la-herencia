"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { fetchContactos, type Contacto, type TipoContacto } from "@/services/contactosApi";
import { filterInputClass } from "@/components/ui/FilterBar";

/**
 * Combobox de selección de contacto (cliente/proveedor/comprador/
 * consignatario/etc.), reemplazo del texto libre usado hasta ahora en los
 * filtros de Compras/Arrendamientos/Ventas Hacienda/Impuestos/
 * Remuneraciones (pedido explícito del usuario: "La seleccion de... debe
 * hacerse a través de listas desplegables").
 *
 * Reusa `/api/contactos` (búsqueda por razón social, opcionalmente
 * acotada por `tipoContacto`). Es de solo lectura desde este componente
 * — no crea contactos (eso vive en la página de alta de Contactos).
 */
export function ContactoSelect({
  value,
  razonSocial,
  onChange,
  tipoContacto,
  placeholder = "Buscar contacto…",
  label,
}: {
  /** IdContacto seleccionado, o null si no hay selección. */
  value: number | null;
  /** Razón social a mostrar cuando `value` viene de afuera (ej. un filtro ya aplicado). */
  razonSocial?: string | null;
  onChange: (idContacto: number | null, razonSocial: string | null) => void;
  tipoContacto?: TipoContacto;
  placeholder?: string;
  label?: string;
}) {
  const [query, setQuery] = useState(razonSocial ?? "");
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setQuery(razonSocial ?? "");
  }, [razonSocial, value]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const { data, isFetching } = useQuery({
    queryKey: ["contactos-select", query, tipoContacto],
    queryFn: () => fetchContactos({ q: query || undefined, tipoContacto, pageSize: 20 }),
    enabled: isOpen && query.length >= 2,
  });

  function handleSelect(contacto: Contacto) {
    onChange(contacto.idContacto, contacto.razonSocial);
    setQuery(contacto.razonSocial ?? "");
    setIsOpen(false);
  }

  function handleClear() {
    onChange(null, null);
    setQuery("");
  }

  return (
    <div ref={containerRef} className="relative flex flex-col gap-1">
      {label && <label className="text-sm text-ink-secondary">{label}</label>}
      <div className="flex items-center gap-1">
        <input
          className={filterInputClass}
          value={query}
          placeholder={placeholder}
          onFocus={() => setIsOpen(true)}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
            if (value != null) onChange(null, null);
          }}
        />
        {value != null && (
          <button
            type="button"
            onClick={handleClear}
            className="rounded-sm border border-border px-1.5 py-1 text-xs text-ink-secondary hover:text-ink-primary"
            title="Quitar selección"
          >
            ✕
          </button>
        )}
      </div>

      {isOpen && query.length >= 2 && (
        <div className="absolute top-full z-10 mt-1 max-h-64 w-full min-w-[16rem] overflow-y-auto rounded-md border border-border bg-surface shadow-lg">
          {isFetching && (
            <p className="px-3 py-2 text-sm text-ink-muted">Buscando…</p>
          )}
          {!isFetching && data && data.items.length === 0 && (
            <p className="px-3 py-2 text-sm text-ink-muted">Sin resultados.</p>
          )}
          {!isFetching &&
            data?.items.map((c) => (
              <button
                key={c.idContacto}
                type="button"
                onClick={() => handleSelect(c)}
                className="flex w-full flex-col items-start gap-0.5 px-3 py-2 text-left text-sm hover:bg-surface-sunken"
              >
                <span className="text-ink-primary">{c.razonSocial}</span>
                <span className="text-xs text-ink-muted">
                  {c.tipoContacto ?? "—"}
                  {c.cuit ? ` · ${c.cuit}` : ""}
                </span>
              </button>
            ))}
        </div>
      )}
    </div>
  );
}
