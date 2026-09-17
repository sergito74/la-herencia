"use client";

import { useEffect, useState } from "react";

import { formatMoneda, normalizarNumeroPegado, parseNumeroLocal, type MonedaFormato } from "@/lib/format";

/**
 * Input numérico editable que respeta la convención de formato de moneda
 * del resto de la app ($ / us$, miles ".", decimales ",") — mientras no
 * tiene foco muestra el valor formateado; al enfocar, pasa a edición en
 * crudo (sin prefijo) para no pelear con el tipeo. El pegado normaliza
 * automáticamente valores en formato US ("60,717.34" → "60717,34").
 */
export function MoneyInput({
  value,
  onChange,
  moneda,
  className,
}: {
  value: number;
  onChange: (value: number) => void;
  moneda: MonedaFormato;
  className?: string;
}) {
  const [focused, setFocused] = useState(false);
  const [texto, setTexto] = useState(String(value || ""));

  useEffect(() => {
    if (!focused) setTexto(String(value || ""));
  }, [value, focused]);

  return (
    <input
      type="text"
      inputMode="decimal"
      className={className}
      value={focused ? texto : formatMoneda(value || 0, moneda)}
      onFocus={() => {
        setFocused(true);
        setTexto(value ? String(value) : "");
      }}
      onChange={(e) => setTexto(e.target.value)}
      onBlur={() => {
        setFocused(false);
        onChange(parseNumeroLocal(texto));
      }}
      onPaste={(e) => {
        e.preventDefault();
        setTexto(normalizarNumeroPegado(e.clipboardData.getData("text")));
      }}
    />
  );
}
