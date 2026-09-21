"use client";

import { useState } from "react";

import { formatNumero, parseNumeroLocal } from "@/lib/format";

/**
 * Celda de grilla numérica: el padre sigue guardando el texto que escribe el
 * usuario (ej. "60717,34", como en un editor tipo planilla), pero cuando la
 * celda no tiene foco se muestra con la convención del sistema (miles ".",
 * decimales ","): "60.717,34". Con foco muestra el texto crudo.
 */
export function CeldaNumerica({
  value,
  onChange,
  onPaste,
  className,
  minDecimales = 0,
  maxDecimales = 3,
}: {
  value: string;
  onChange: (value: string) => void;
  onPaste?: (e: React.ClipboardEvent<HTMLInputElement>) => void;
  className?: string;
  minDecimales?: number;
  maxDecimales?: number;
}) {
  const [focused, setFocused] = useState(false);
  const mostrar =
    focused || value.trim() === "" ? value : formatNumero(parseNumeroLocal(value), { min: minDecimales, max: maxDecimales });
  return (
    <input
      className={className}
      inputMode="decimal"
      value={mostrar}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
      onChange={(e) => onChange(e.target.value)}
      onPaste={onPaste}
    />
  );
}
