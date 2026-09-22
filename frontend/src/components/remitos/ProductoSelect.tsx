"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useId, useRef, useState } from "react";

import { buscarProductos, type Producto } from "@/services/remitosApi";
import { filterInputClass } from "@/components/ui/FilterBar";

/**
 * Buscador de insumos (agroquímicos, fertilizantes y semillas): 9.516 productos del
 * catálogo unificado. Los que ya se usan en remitos (con unidad base) aparecen primero.
 */
export function ProductoSelect({
  value,
  onChange,
  disabled,
  placeholder = "Buscar producto…",
  className,
}: {
  value: { idProducto: number; producto: string } | null;
  onChange: (p: Producto) => void;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
}) {
  const [texto, setTexto] = useState(value?.producto ?? "");
  const [abierto, setAbierto] = useState(false);
  const [indice, setIndice] = useState(0);
  const contenedor = useRef<HTMLDivElement | null>(null);
  const listaId = useId();

  useEffect(() => {
    setTexto(value?.producto ?? "");
  }, [value?.idProducto, value?.producto]);

  useEffect(() => {
    const fuera = (e: MouseEvent) => {
      if (contenedor.current && !contenedor.current.contains(e.target as Node)) setAbierto(false);
    };
    document.addEventListener("mousedown", fuera);
    return () => document.removeEventListener("mousedown", fuera);
  }, []);

  const buscando = abierto && texto.trim().length >= 2 && texto !== value?.producto;
  const { data, isFetching } = useQuery({
    queryKey: ["productos-select", texto],
    queryFn: () => buscarProductos(texto.trim()),
    enabled: buscando,
    staleTime: 60_000,
  });
  const items = data ?? [];

  function elegir(p: Producto) {
    onChange(p);
    setTexto(p.producto);
    setAbierto(false);
  }

  return (
    <div ref={contenedor} className={`relative ${className ?? ""}`}>
      <input
        className={`${filterInputClass} w-full px-1.5 py-1 text-xs`}
        value={texto}
        disabled={disabled}
        placeholder={placeholder}
        onFocus={() => setAbierto(true)}
        onChange={(e) => {
          setTexto(e.target.value);
          setAbierto(true);
          setIndice(0);
        }}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") {
            e.preventDefault();
            setIndice((i) => Math.min(i + 1, items.length - 1));
          } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setIndice((i) => Math.max(i - 1, 0));
          } else if (e.key === "Enter" && abierto && items[indice]) {
            e.preventDefault();
            elegir(items[indice]);
          } else if (e.key === "Escape") setAbierto(false);
        }}
        role="combobox"
        aria-expanded={abierto}
        aria-controls={listaId}
        aria-autocomplete="list"
      />
      {abierto && texto.trim().length >= 2 && texto !== value?.producto && (
        <ul id={listaId} className="absolute z-30 mt-1 max-h-64 w-[26rem] max-w-[90vw] overflow-auto rounded-md border border-border bg-surface text-xs shadow-lg" role="listbox">
          {isFetching && <li className="px-2 py-1 text-ink-secondary">Buscando…</li>}
          {!isFetching && items.length === 0 && <li className="px-2 py-1 text-ink-secondary">Sin resultados.</li>}
          {items.map((p, i) => (
            <li
              key={p.idProducto}
              role="option"
              aria-selected={i === indice}
              onMouseDown={(e) => {
                e.preventDefault();
                elegir(p);
              }}
              onMouseEnter={() => setIndice(i)}
              className={`cursor-pointer px-2 py-1 ${i === indice ? "bg-finance-light" : ""}`}
            >
              <span className="font-medium">{p.producto}</span>{" "}
              <span className="text-ink-secondary">
                · {p.tipo ?? "—"}
                {p.ingredienteActivo ? ` · ${p.ingredienteActivo}` : ""}
                {p.unidadBase ? ` · ${p.unidadBase}` : ""}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
