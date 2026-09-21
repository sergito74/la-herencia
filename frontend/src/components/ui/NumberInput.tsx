"use client";

import { useEffect, useState } from "react";

import { formatNumero, normalizarNumeroPegado, numeroAEdicionLocal, parseNumeroLocal } from "@/lib/format";

/**
 * Input numérico (sin símbolo de moneda) con la convención de formato del
 * sistema: sin foco muestra el valor con miles "." y decimales ","; con foco
 * pasa a edición en crudo para no pelear con el tipeo. Reemplaza a
 * `<input type="number">`, que nunca muestra separador de miles. Para
 * importes en pesos/dólares usar `MoneyInput`.
 */
export function NumberInput({
  value,
  onChange,
  minDecimales = 0,
  maxDecimales = 3,
  className,
  required,
  disabled,
  placeholder,
  title,
}: {
  value: number | null;
  onChange: (value: number | null) => void;
  minDecimales?: number;
  maxDecimales?: number;
  className?: string;
  required?: boolean;
  disabled?: boolean;
  placeholder?: string;
  title?: string;
}) {
  const [focused, setFocused] = useState(false);
  const aEdicion = (v: number | null) => (v == null ? "" : numeroAEdicionLocal(v));
  const [texto, setTexto] = useState(aEdicion(value));

  useEffect(() => {
    if (!focused) setTexto(aEdicion(value));
  }, [value, focused]);

  return (
    <input
      type="text"
      inputMode="decimal"
      className={className}
      required={required}
      disabled={disabled}
      placeholder={placeholder}
      title={title}
      value={focused ? texto : value == null ? "" : formatNumero(value, { min: minDecimales, max: maxDecimales })}
      onFocus={() => {
        setFocused(true);
        setTexto(aEdicion(value));
      }}
      onChange={(e) => setTexto(e.target.value)}
      onBlur={() => {
        setFocused(false);
        onChange(texto.trim() === "" ? null : parseNumeroLocal(texto));
      }}
      onPaste={(e) => {
        e.preventDefault();
        setTexto(normalizarNumeroPegado(e.clipboardData.getData("text")));
      }}
    />
  );
}
