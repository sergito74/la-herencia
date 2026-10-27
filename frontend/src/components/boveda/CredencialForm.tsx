"use client";

import type { CredencialNueva, DatoEntrada } from "@/services/bovedaApi";

export const CREDENCIAL_VACIA: CredencialNueva = {
  nombre: "",
  titular: "empresa",
  idSocio: null,
  usuario: "",
  clave: "",
  datos: [],
};

const inputCls = "w-full rounded-md border border-border bg-surface px-2 py-1 text-sm";

/** Campos de una credencial (042, T015). La contraseña y los datos secretos
 * van en campos `password` sin autocompletar; al editar una existente, dejar
 * un secreto vacío conserva el valor guardado. */
export function CredencialForm({
  value,
  onChange,
  conClave = true,
}: {
  value: CredencialNueva;
  onChange: (v: CredencialNueva) => void;
  conClave?: boolean;
}) {
  const set = (cambio: Partial<CredencialNueva>) => onChange({ ...value, ...cambio });
  const setDato = (i: number, cambio: Partial<DatoEntrada>) =>
    set({ datos: value.datos.map((d, j) => (j === i ? { ...d, ...cambio } : d)) });

  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
      <label className="text-sm">
        Nombre de la credencial
        <input className={inputCls} value={value.nombre} maxLength={80} required
          placeholder="ej. Clave Fiscal Giamigli" onChange={(e) => set({ nombre: e.target.value })} />
      </label>
      <label className="text-sm">
        Titular
        <select className={inputCls} value={value.titular}
          onChange={(e) => set({ titular: e.target.value as CredencialNueva["titular"] })}>
          <option value="empresa">Empresa</option>
          <option value="socio">Socio</option>
        </select>
      </label>
      {value.titular === "socio" && (
        <label className="text-sm">
          Nº de socio
          <input className={inputCls} inputMode="numeric" value={value.idSocio ?? ""}
            onChange={(e) => set({ idSocio: e.target.value ? Number(e.target.value.replace(/\D/g, "")) : null })} />
        </label>
      )}
      <label className="text-sm">
        Usuario
        <input className={inputCls} value={value.usuario ?? ""} maxLength={120} autoComplete="off"
          onChange={(e) => set({ usuario: e.target.value })} />
      </label>
      {conClave && (
        <label className="text-sm">
          Contraseña
          <input className={inputCls} type="password" autoComplete="new-password" maxLength={200}
            value={value.clave ?? ""} onChange={(e) => set({ clave: e.target.value })} />
        </label>
      )}
      <div className="md:col-span-2">
        <p className="text-sm">Datos adicionales de ingreso (CUIT, nº de cliente, PIN…)</p>
        {value.datos.map((d, i) => (
          <div key={i} className="mt-1 flex items-center gap-2">
            <input className={`${inputCls} max-w-[12rem]`} placeholder="Nombre" maxLength={60} value={d.nombre}
              onChange={(e) => setDato(i, { nombre: e.target.value })} />
            <input className={inputCls} placeholder={d.secreto ? "Vacío = conservar el guardado" : "Valor"}
              type={d.secreto ? "password" : "text"} autoComplete={d.secreto ? "new-password" : "off"} maxLength={200}
              value={d.valor ?? ""} onChange={(e) => setDato(i, { valor: e.target.value })} />
            <label className="flex shrink-0 items-center gap-1 text-xs">
              <input type="checkbox" checked={d.secreto} onChange={(e) => setDato(i, { secreto: e.target.checked })} />
              Secreto
            </label>
            <button type="button" className="text-xs text-red-700 underline"
              onClick={() => set({ datos: value.datos.filter((_, j) => j !== i) })}>
              Quitar
            </button>
          </div>
        ))}
        <button type="button" className="mt-1 text-xs text-finance underline"
          onClick={() => set({ datos: [...value.datos, { nombre: "", secreto: false, valor: "" }] })}>
          Agregar dato
        </button>
      </div>
    </div>
  );
}
