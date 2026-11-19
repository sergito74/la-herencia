"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { useAuth } from "@/components/auth/AuthContext";
import { apiGet } from "@/services/apiClient";

/** Búsqueda global Ctrl+K (spec 051 US4): contactos, compras por número, productos, lotes, órdenes, pantallas y
 * acciones. Solo navega; no modifica nada. Teclado: flechas, Enter, Esc. */
type Resultado = { tipo: string; titulo: string; subtitulo?: string; href: string; alta?: boolean };
type DelServidor = { tipo: string; titulo: string; subtitulo?: string; idContacto?: number; idCompra?: number; idProducto?: number; idLote?: number; idOrden?: number };

const PANTALLAS: Resultado[] = [
  ["Inicio", "/"], ["Tesorería", "/finanzas/tesoreria"], ["Cuentas corrientes", "/finanzas/cuentas-corrientes"],
  ["Saldos de proveedores", "/finanzas/cuentas-corrientes/saldos"], ["Órdenes de pago", "/finanzas/ordenes-pago"],
  ["Cajas y socios", "/finanzas/cajas"], ["Flujo de caja", "/finanzas/flujo-caja-real"], ["Facturas esperadas", "/finanzas/facturas-esperadas"],
  ["Tarjetas", "/finanzas/tarjetas"], ["Impuestos", "/finanzas/impuestos"], ["Compras", "/compras"], ["Ventas de hacienda", "/ventas/hacienda"],
  ["Ventas de granos", "/ventas/granos"], ["Pastaje", "/ventas/pastaje"], ["Órdenes de trabajo", "/produccion/ordenes"],
  ["Planificación agrícola", "/produccion/planificacion"], ["Remitos", "/produccion/remitos"], ["Stock de insumos", "/produccion/stock"],
  ["Resultado de cultivo", "/produccion/resultado-cultivo"], ["Imputación de costos", "/imputacion/documentos"], ["Remuneraciones", "/personal/remuneraciones"],
  ["Trabajos eventuales", "/personal/trabajos-eventuales"], ["Contactos", "/contactos"], ["Bóveda de portales", "/boveda"],
].map(([titulo, href]) => ({ tipo: "Pantallas", titulo, href }));

const ACCIONES: Resultado[] = [
  { tipo: "Acciones", titulo: "Nueva compra", href: "/compras/nueva", alta: true },
  { tipo: "Acciones", titulo: "Nueva orden de trabajo", href: "/produccion/ordenes/nuevo", alta: true },
  { tipo: "Acciones", titulo: "Leer la planilla de Matías", href: "/produccion/ordenes", alta: true },
  { tipo: "Acciones", titulo: "Nuevo trabajo eventual", href: "/personal/trabajos-eventuales", alta: true },
  { tipo: "Acciones", titulo: "Movimiento de caja", href: "/finanzas/cajas", alta: true },
];

function destino(r: DelServidor): string {
  if (r.idContacto != null) return `/finanzas/cuentas-corrientes?idContacto=${r.idContacto}&razonSocial=${encodeURIComponent(r.titulo)}`;
  if (r.idCompra != null) return `/compras/${r.idCompra}/editar`;
  if (r.idOrden != null) return `/produccion/ordenes/${r.idOrden}/editar`;
  if (r.idLote != null) return "/produccion/planificacion";
  return "/produccion/stock";
}

const sinAcentos = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

export function BusquedaGlobal() {
  const [abierta, setAbierta] = useState(false);
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");
  const [sel, setSel] = useState(0);
  const router = useRouter();
  const pathname = usePathname();
  const { usuario } = useAuth();
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setAbierta((v) => !v); }
    };
    const abrir = () => setAbierta(true);
    window.addEventListener("keydown", tecla);
    window.addEventListener("abrir-busqueda", abrir);
    return () => { window.removeEventListener("keydown", tecla); window.removeEventListener("abrir-busqueda", abrir); };
  }, []);
  useEffect(() => { if (abierta) { setQ(""); setSel(0); setTimeout(() => input.current?.focus(), 0); } }, [abierta]);
  useEffect(() => { const t = setTimeout(() => setDebounced(q.trim()), 200); return () => clearTimeout(t); }, [q]);
  useEffect(() => setAbierta(false), [pathname]);

  const servidor = useQuery({
    queryKey: ["buscar", debounced], enabled: abierta && debounced.length >= 2,
    queryFn: () => apiGet<DelServidor[]>("/api/buscar", { q: debounced }),
  });

  const resultados = useMemo<Resultado[]>(() => {
    const t = sinAcentos(q.trim());
    const lectura = usuario?.rol === "Lectura";
    const locales = [...ACCIONES.filter((a) => !(lectura && a.alta)), ...PANTALLAS]
      .filter((r) => !t || sinAcentos(r.titulo).includes(t));
    const remotos = t.length >= 2 ? (servidor.data ?? []).map((r) => ({ tipo: r.tipo, titulo: r.titulo, subtitulo: r.subtitulo, href: destino(r) })) : [];
    return t ? [...remotos, ...locales] : [...ACCIONES.filter((a) => !(lectura && a.alta)), ...PANTALLAS.slice(0, 6)];
  }, [q, servidor.data, usuario]);

  useEffect(() => setSel(0), [resultados.length]);
  if (!abierta || pathname === "/login") return null;

  const ir = (r?: Resultado) => { if (!r) return; setAbierta(false); router.push(r.href); };
  let grupoAnterior = "";

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-ink-primary/30 px-4 pt-[12vh]" onMouseDown={() => setAbierta(false)}>
      <div role="dialog" aria-label="Buscar en el sistema" className="w-full max-w-xl overflow-hidden rounded-xl border border-border bg-surface shadow-2xl" onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-3 border-b border-border px-4">
          <svg viewBox="0 0 24 24" className="h-5 w-5 text-ink-muted" fill="none" stroke="currentColor" strokeWidth={1.8} aria-hidden><circle cx="11" cy="11" r="6" /><path d="m20 20-4.5-4.5" /></svg>
          <input ref={input} value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar proveedor, número de factura, producto, lote, orden o pantalla…"
            aria-label="Buscar" className="h-12 flex-1 bg-transparent text-sm outline-none placeholder:text-ink-muted"
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") { e.preventDefault(); setSel((s) => Math.min(s + 1, resultados.length - 1)); }
              else if (e.key === "ArrowUp") { e.preventDefault(); setSel((s) => Math.max(s - 1, 0)); }
              else if (e.key === "Enter") { e.preventDefault(); ir(resultados[sel]); }
              else if (e.key === "Escape") setAbierta(false);
            }} />
          <kbd className="rounded border border-border px-1.5 text-[11px] text-ink-muted">Esc</kbd>
        </div>
        <ul className="max-h-[60vh] overflow-y-auto py-2" role="listbox">
          {resultados.length === 0 && (
            <li className="px-4 py-6 text-center text-sm text-ink-secondary">{servidor.isFetching ? "Buscando…" : "Sin resultados. Probá con parte del nombre o del número."}</li>
          )}
          {resultados.map((r, i) => {
            const encabezado = r.tipo !== grupoAnterior ? r.tipo : null;
            grupoAnterior = r.tipo;
            return (
              <li key={`${r.tipo}-${r.href}-${r.titulo}-${i}`}>
                {encabezado && <p className="px-4 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wide text-ink-muted">{encabezado}</p>}
                <button type="button" role="option" aria-selected={i === sel} onMouseEnter={() => setSel(i)} onClick={() => ir(r)}
                  className={`flex w-full items-center justify-between gap-3 px-4 py-2 text-left text-sm ${i === sel ? "bg-finance-light text-finance" : "text-ink-primary"}`}>
                  <span className="min-w-0 truncate">{r.titulo}</span>
                  {r.subtitulo && <span className="shrink-0 truncate text-xs text-ink-secondary">{r.subtitulo}</span>}
                </button>
              </li>
            );
          })}
        </ul>
        <div className="flex gap-4 border-t border-border bg-surface-sunken/60 px-4 py-2 text-[11px] text-ink-muted">
          <span>↑↓ moverse</span><span>Enter abrir</span><span>Esc cerrar</span>
        </div>
      </div>
    </div>
  );
}
