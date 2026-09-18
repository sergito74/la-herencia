"use client";

import { useId, useState } from "react";

import {
  crearCampania,
  crearCentroCosto,
  crearDestino,
  crearRubro,
  fetchRubroSugerido,
  type FiltrosComprasResponse,
  type LineaInput,
} from "@/services/comprasApi";
import { formatMonto, formatMoneda, normalizarNumeroPegado, parseNumeroLocal, type MonedaFormato } from "@/lib/format";
import { useToast } from "@/components/ui/Toast";

/**
 * Grilla de líneas de compra estilo planilla de cálculo (pedido explícito
 * del usuario). Rubro/Centro de Costos/Destino/Campaña son catálogos
 * cerrados (no admiten texto libre) — se cargan por `<select>` restringido
 * a los valores existentes; agregar uno nuevo requiere una confirmación
 * explícita del usuario (`window.confirm`) antes de escribirlo en la base.
 */
export interface GridRow {
  cantidad: string;
  unidad: string;
  productoServicio: string;
  rubro: string;
  centroCosto: string;
  destino: string;
  campania: string;
  precioUnitario: string;
  iva: string;
}

export const FILA_VACIA: GridRow = {
  cantidad: "",
  unidad: "",
  productoServicio: "",
  rubro: "",
  centroCosto: "",
  destino: "",
  campania: "",
  precioUnitario: "",
  iva: "",
};

const COLUMNAS_EDITABLES = [
  "cantidad",
  "unidad",
  "productoServicio",
  "rubro",
  "centroCosto",
  "destino",
  "campania",
  "precioUnitario",
  "iva",
] as const;

type ColumnaEditable = (typeof COLUMNAS_EDITABLES)[number];
type ColumnaCatalogo = "rubro" | "centroCosto" | "destino" | "campania";

const NUEVO_SENTINEL = "__nuevo__";

function esFilaVacia(row: GridRow): boolean {
  return Object.values(row).every((v) => v.trim() === "");
}

export function calcularLinea(row: GridRow) {
  const subtotal = parseNumeroLocal(row.cantidad) * parseNumeroLocal(row.precioUnitario);
  const importeIva = (subtotal * parseNumeroLocal(row.iva)) / 100;
  return { subtotal, importeIva };
}

/** Convierte las filas no vacías de la grilla al contrato `LineaInput` de la API,
 * resolviendo Rubro/Centro de Costos/Destino (texto elegido del catálogo) a su id real. */
export function filasARequestLineas(rows: GridRow[], filtros: FiltrosComprasResponse | undefined): LineaInput[] {
  const matchId = <T,>(
    texto: string,
    catalogo: T[] | undefined,
    getLabel: (t: T) => string | null,
    getId: (t: T) => number
  ): number | null => {
    if (!texto.trim() || !catalogo) return null;
    const found = catalogo.find((item) => (getLabel(item) ?? "").trim().toLowerCase() === texto.trim().toLowerCase());
    return found ? getId(found) : null;
  };

  return rows
    .filter((r) => !esFilaVacia(r))
    .map((r) => ({
      productoServicio: r.productoServicio,
      cantidad: parseNumeroLocal(r.cantidad),
      precioUnitario: parseNumeroLocal(r.precioUnitario),
      iva: parseNumeroLocal(r.iva),
      unidad: r.unidad || null,
      idCentroCosto: matchId(r.centroCosto, filtros?.centrosCosto, (c) => c.centroCosto, (c) => c.idCentroCosto),
      idDestino: matchId(r.destino, filtros?.destinos, (d) => d.destino, (d) => d.idDestino),
      idRubro: matchId(r.rubro, filtros?.rubros, (rb) => rb.rubro, (rb) => rb.idRubro),
      campaña: r.campania || null,
      ajusteFinanciero: false,
    }));
}

const inputClass =
  "w-full border-0 bg-transparent px-1.5 py-0.5 text-xs text-ink-primary focus:bg-finance-light focus:outline-none";
const selectClass = `${inputClass} cursor-pointer`;

export function ComprasGrid({
  rows,
  onChange,
  filtros,
  moneda,
  onCatalogoActualizado,
}: {
  rows: GridRow[];
  onChange: (rows: GridRow[]) => void;
  filtros: FiltrosComprasResponse | undefined;
  moneda: MonedaFormato;
  /** Se llama tras crear un valor de catálogo nuevo, para que el padre refresque `filtros`. */
  onCatalogoActualizado: () => void;
}) {
  const { showToast } = useToast();
  const listIdBase = useId();
  const unidadesListId = `${listIdBase}-unidades`;
  // Precio unitario: crudo mientras se edita (no pelear con el tipeo),
  // formateado con separador de miles apenas se pierde el foco.
  const [filaPrecioEnFoco, setFilaPrecioEnFoco] = useState<number | null>(null);

  function actualizarCelda(rowIndex: number, key: ColumnaEditable, value: string) {
    const next = rows.map((r, i) => (i === rowIndex ? { ...r, [key]: value } : r));
    // Crecimiento automático: si ya no queda ninguna fila vacía, agregar 10 más.
    if (!next.some(esFilaVacia)) {
      for (let i = 0; i < 10; i++) next.push({ ...FILA_VACIA });
    }
    onChange(next);
  }

  async function handleProductoBlur(rowIndex: number) {
    const row = rows[rowIndex];
    if (row.rubro.trim() || !row.productoServicio.trim()) return;
    try {
      const sugerido = await fetchRubroSugerido(row.productoServicio);
      if (sugerido.rubro) actualizarCelda(rowIndex, "rubro", sugerido.rubro);
    } catch {
      // Sugerencia best-effort — si falla, el usuario completa el rubro manualmente.
    }
  }

  async function handleCatalogoChange(rowIndex: number, columna: ColumnaCatalogo, value: string) {
    if (value !== NUEVO_SENTINEL) {
      actualizarCelda(rowIndex, columna, value);
      return;
    }

    const etiqueta: Record<ColumnaCatalogo, string> = {
      rubro: "Rubro",
      centroCosto: "Centro de Costos",
      destino: "Destino",
      campania: "Campaña",
    };
    const nombre = window.prompt(`Nombre del nuevo ${etiqueta[columna]}:`);
    if (!nombre || !nombre.trim()) return;
    const confirmado = window.confirm(
      `¿Confirmás agregar "${nombre.trim()}" como un nuevo valor permanente de ${etiqueta[columna]}? Esta acción no se puede deshacer desde acá.`
    );
    if (!confirmado) return;

    try {
      let etiquetaCreada: string;
      if (columna === "rubro") etiquetaCreada = (await crearRubro(nombre.trim())).rubro ?? nombre.trim();
      else if (columna === "centroCosto")
        etiquetaCreada = (await crearCentroCosto(nombre.trim())).centroCosto ?? nombre.trim();
      else if (columna === "destino") etiquetaCreada = (await crearDestino(nombre.trim())).destino ?? nombre.trim();
      else etiquetaCreada = (await crearCampania(nombre.trim())).campania ?? nombre.trim();

      onCatalogoActualizado();
      actualizarCelda(rowIndex, columna, etiquetaCreada);
      showToast(`${etiqueta[columna]} "${etiquetaCreada}" agregado.`, "success");
    } catch {
      showToast(`No se pudo crear el ${etiqueta[columna].toLowerCase()}. Intentá de nuevo.`, "danger");
    }
  }

  /** Rubro/Centro de Costos/Destino/Campaña son catálogos cerrados — un pegado
   * multi-celda que caiga en esas columnas solo se acepta si matchea EXACTO
   * (case-insensitive) un valor existente; si no, la celda queda vacía en
   * vez de colar texto libre (mismo criterio que el `<select>`, ver SelectCatalogo). */
  function resolverValorCatalogoPegado(col: ColumnaCatalogo, texto: string): string {
    const catalogos: Record<ColumnaCatalogo, string[]> = {
      rubro: (filtros?.rubros ?? []).map((r) => r.rubro ?? ""),
      centroCosto: (filtros?.centrosCosto ?? []).map((c) => c.centroCosto ?? ""),
      destino: (filtros?.destinos ?? []).map((d) => d.destino ?? ""),
      campania: (filtros?.campañas ?? []).map((c) => c.campania ?? ""),
    };
    const match = catalogos[col].find((v) => v.trim().toLowerCase() === texto.trim().toLowerCase());
    return match ?? "";
  }

  function handlePaste(rowIndex: number, colIndex: number, e: React.ClipboardEvent<HTMLInputElement>) {
    // Siempre interceptado (incluso pegado de una sola celda): el pegado
    // nativo del navegador no normaliza números en formato US (ver bug
    // reportado — "60,717.34" pegado sin pasar por `normalizarNumeroPegado`
    // se interpretaba mal, ej. como 60,72).
    const texto = e.clipboardData.getData("text");
    e.preventDefault();
    const filasPegadas = texto.replace(/\r/g, "").split("\n").filter((_, i, arr) => !(i === arr.length - 1 && arr[i] === ""));
    const next = [...rows];
    while (next.length < rowIndex + filasPegadas.length) next.push({ ...FILA_VACIA });

    const columnasNumericas: ColumnaEditable[] = ["cantidad", "precioUnitario", "iva"];
    const columnasCatalogo: ColumnaEditable[] = ["rubro", "centroCosto", "destino", "campania"];

    filasPegadas.forEach((linea, dRow) => {
      const celdas = linea.split("\t");
      celdas.forEach((valor, dCol) => {
        const col = COLUMNAS_EDITABLES[colIndex + dCol];
        if (!col) return;
        let valorFinal = valor;
        if (columnasNumericas.includes(col)) valorFinal = normalizarNumeroPegado(valor);
        else if (columnasCatalogo.includes(col)) valorFinal = resolverValorCatalogoPegado(col as ColumnaCatalogo, valor);
        next[rowIndex + dRow] = { ...next[rowIndex + dRow], [col]: valorFinal };
      });
    });

    if (!next.some(esFilaVacia)) {
      for (let i = 0; i < 10; i++) next.push({ ...FILA_VACIA });
    }
    onChange(next);
  }

  const totalSubtotal = rows.reduce((acc, r) => acc + calcularLinea(r).subtotal, 0);
  const totalIva = rows.reduce((acc, r) => acc + calcularLinea(r).importeIva, 0);

  function SelectCatalogo({
    rowIndex,
    columna,
    value,
    opciones,
    placeholderDefault,
  }: {
    rowIndex: number;
    columna: ColumnaCatalogo;
    value: string;
    opciones: string[];
    placeholderDefault?: string;
  }) {
    return (
      <select
        className={selectClass}
        value={value}
        onChange={(e) => handleCatalogoChange(rowIndex, columna, e.target.value)}
      >
        <option value="">{placeholderDefault ?? "—"}</option>
        {opciones.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
        <option value={NUEVO_SENTINEL}>+ Agregar nuevo…</option>
      </select>
    );
  }

  return (
    <div className="space-y-1">
      <datalist id={unidadesListId}>
        {filtros?.unidadesMedida.map((u) => <option key={u.unidad} value={u.unidad} />)}
      </datalist>

      <div className="overflow-x-auto rounded-md border border-border">
        <table className="min-w-full divide-y divide-border text-xs">
          <thead className="sticky top-0 bg-surface-sunken text-left">
            <tr>
              {[
                "Cantidad",
                "Unidad",
                "Producto/Servicio",
                "Rubro",
                "Centro de Costos",
                "Destino",
                "Campaña",
                "Precio unitario",
                "IVA %",
                "IVA $",
                "Subtotal",
              ].map((h) => (
                <th key={h} className="whitespace-nowrap px-1.5 py-1 font-medium text-ink-secondary">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.map((row, rowIndex) => {
              const { subtotal, importeIva } = calcularLinea(row);
              const filaIniciada = !esFilaVacia(row);
              return (
                <tr key={rowIndex} className="hover:bg-surface-sunken">
                  <td className="w-24">
                    <input
                      className={`${inputClass} font-data text-right`}
                      value={row.cantidad}
                      onChange={(e) => actualizarCelda(rowIndex, "cantidad", e.target.value)}
                      onPaste={(e) => handlePaste(rowIndex, 0, e)}
                    />
                  </td>
                  <td className="w-24">
                    <input
                      className={inputClass}
                      list={unidadesListId}
                      value={row.unidad}
                      onChange={(e) => actualizarCelda(rowIndex, "unidad", e.target.value)}
                      onPaste={(e) => handlePaste(rowIndex, 1, e)}
                    />
                  </td>
                  <td className="min-w-[14rem]">
                    <input
                      className={inputClass}
                      value={row.productoServicio}
                      onChange={(e) => actualizarCelda(rowIndex, "productoServicio", e.target.value)}
                      onBlur={() => handleProductoBlur(rowIndex)}
                      onPaste={(e) => handlePaste(rowIndex, 2, e)}
                    />
                  </td>
                  <td className="min-w-[10rem]">
                    <SelectCatalogo
                      rowIndex={rowIndex}
                      columna="rubro"
                      value={row.rubro}
                      opciones={(filtros?.rubros ?? []).map((r) => r.rubro ?? "").filter(Boolean)}
                    />
                  </td>
                  <td className="min-w-[10rem]">
                    <SelectCatalogo
                      rowIndex={rowIndex}
                      columna="centroCosto"
                      value={row.centroCosto}
                      opciones={(filtros?.centrosCosto ?? []).map((c) => c.centroCosto ?? "").filter(Boolean)}
                      placeholderDefault={filaIniciada ? "Adm. General" : undefined}
                    />
                  </td>
                  <td className="min-w-[10rem]">
                    <SelectCatalogo
                      rowIndex={rowIndex}
                      columna="destino"
                      value={row.destino}
                      opciones={(filtros?.destinos ?? []).map((d) => d.destino ?? "").filter(Boolean)}
                      placeholderDefault={filaIniciada ? "General" : undefined}
                    />
                  </td>
                  <td className="min-w-[8rem]">
                    <SelectCatalogo
                      rowIndex={rowIndex}
                      columna="campania"
                      value={row.campania}
                      opciones={(filtros?.campañas ?? []).map((c) => c.campania ?? "").filter(Boolean)}
                      placeholderDefault={filaIniciada ? "No Aplica" : undefined}
                    />
                  </td>
                  <td className="w-28">
                    <input
                      className={`${inputClass} font-data text-right`}
                      value={
                        filaPrecioEnFoco === rowIndex || !row.precioUnitario
                          ? row.precioUnitario
                          : formatMonto(parseNumeroLocal(row.precioUnitario))
                      }
                      onFocus={() => setFilaPrecioEnFoco(rowIndex)}
                      onChange={(e) => actualizarCelda(rowIndex, "precioUnitario", e.target.value)}
                      onBlur={() => setFilaPrecioEnFoco(null)}
                      onPaste={(e) => handlePaste(rowIndex, 7, e)}
                    />
                  </td>
                  <td className="w-20">
                    <input
                      className={`${inputClass} font-data text-right`}
                      value={row.iva}
                      onChange={(e) => actualizarCelda(rowIndex, "iva", e.target.value)}
                      onPaste={(e) => handlePaste(rowIndex, 8, e)}
                    />
                  </td>
                  <td className="w-24 px-1.5 py-0.5 text-right font-data text-ink-secondary">
                    {importeIva ? formatMoneda(importeIva, moneda) : ""}
                  </td>
                  <td className="w-24 px-1.5 py-0.5 text-right font-data text-ink-secondary">
                    {subtotal ? formatMoneda(subtotal, moneda) : ""}
                  </td>
                </tr>
              );
            })}
          </tbody>
          <tfoot className="sticky bottom-0 bg-surface-sunken font-medium">
            <tr>
              <td colSpan={9} className="px-1.5 py-1 text-right text-ink-secondary">
                Totales del cuerpo:
              </td>
              <td className="px-1.5 py-1 text-right font-data">{formatMoneda(totalIva, moneda)}</td>
              <td className="px-1.5 py-1 text-right font-data">{formatMoneda(totalSubtotal, moneda)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}
