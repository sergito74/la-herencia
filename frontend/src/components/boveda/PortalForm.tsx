"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { CREDENCIAL_VACIA, CredencialForm } from "@/components/boveda/CredencialForm";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import {
  getConectores, getCredenciales, type CredencialNueva, type PortalEntrada, type TipoPortal,
} from "@/services/bovedaApi";

const inputCls = "w-full rounded-md border border-border bg-surface px-2 py-1 text-sm";

const TIPOS: { value: TipoPortal; label: string }[] = [
  { value: "organismo", label: "Organismo" },
  { value: "proveedor", label: "Proveedor" },
  { value: "cliente", label: "Cliente" },
  { value: "banco", label: "Banco" },
  { value: "otro", label: "Otro" },
];

type ModoCredencial = "ninguna" | "existente" | "nueva";

export interface PortalFormInicial {
  nombre: string;
  url: string;
  tipo: TipoPortal;
  idContacto: number | null;
  contacto: string | null;
  idCredencial: number | null;
  codigoConector: string | null;
  notas: string | null;
}

/** Alta y edición de un portal (042, T015/T036). Sin conector el portal queda
 * "solo bóveda": guarda el enlace y la credencial, pero el sistema no entra. */
export function PortalForm({
  inicial,
  edicion = false,
  enviando,
  error,
  onSubmit,
  onCancel,
}: {
  inicial?: PortalFormInicial;
  edicion?: boolean;
  enviando: boolean;
  error: string | null;
  onSubmit: (body: PortalEntrada) => void;
  onCancel: () => void;
}) {
  const credenciales = useQuery({ queryKey: ["boveda", "credenciales"], queryFn: getCredenciales });
  const conectores = useQuery({ queryKey: ["boveda", "conectores"], queryFn: getConectores });

  const [nombre, setNombre] = useState(inicial?.nombre ?? "");
  const [url, setUrl] = useState(inicial?.url ?? "https://");
  const [tipo, setTipo] = useState<TipoPortal>(inicial?.tipo ?? "proveedor");
  const [idContacto, setIdContacto] = useState<number | null>(inicial?.idContacto ?? null);
  const [contacto, setContacto] = useState<string | null>(inicial?.contacto ?? null);
  const [codigoConector, setCodigoConector] = useState<string>(inicial?.codigoConector ?? "");
  const [notas, setNotas] = useState(inicial?.notas ?? "");
  const [modo, setModo] = useState<ModoCredencial>(inicial?.idCredencial ? "existente" : edicion ? "ninguna" : "nueva");
  const [idCredencial, setIdCredencial] = useState<number | null>(inicial?.idCredencial ?? null);
  const [nueva, setNueva] = useState<CredencialNueva>(CREDENCIAL_VACIA);

  function enviar(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({
      nombre: nombre.trim(),
      url: url.trim(),
      tipo,
      idContacto,
      idCredencial: modo === "existente" ? idCredencial : null,
      credencialNueva:
        modo === "nueva"
          ? {
              ...nueva,
              nombre: nueva.nombre.trim() || nombre.trim(),
              usuario: nueva.usuario?.trim() || null,
              clave: nueva.clave || null,
              datos: nueva.datos.filter((d) => d.nombre.trim() && d.valor),
            }
          : null,
      codigoConector: codigoConector || null,
      notas: notas.trim() || null,
    });
  }

  return (
    <form onSubmit={enviar} className="space-y-4 rounded-md border border-border bg-surface p-4" autoComplete="off">
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <label className="text-sm">
          Nombre del portal
          <input className={inputCls} value={nombre} maxLength={80} required onChange={(e) => setNombre(e.target.value)} />
        </label>
        <label className="text-sm">
          Enlace de acceso
          <input className={inputCls} type="url" value={url} maxLength={400} required pattern="https?://.+"
            onChange={(e) => setUrl(e.target.value)} />
        </label>
        <label className="text-sm">
          Tipo
          <select className={inputCls} value={tipo} onChange={(e) => setTipo(e.target.value as TipoPortal)}>
            {TIPOS.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </label>
        <div className="text-sm">
          <ContactoSelect label="Contacto del sistema (opcional)" value={idContacto} razonSocial={contacto}
            onChange={(id, rs) => { setIdContacto(id); setContacto(rs); }} />
        </div>
        <label className="text-sm">
          Descarga automática
          <select className={inputCls} value={codigoConector} onChange={(e) => setCodigoConector(e.target.value)}>
            <option value="">Ninguna (solo bóveda)</option>
            {(conectores.data ?? []).map((c) => (
              <option key={c.codigo ?? ""} value={c.codigo ?? ""}>{c.nombre ?? c.codigo}</option>
            ))}
          </select>
        </label>
        <label className="text-sm md:col-span-2">
          Notas
          <textarea className={inputCls} rows={2} maxLength={1000} value={notas} onChange={(e) => setNotas(e.target.value)} />
        </label>
      </div>

      <fieldset className="space-y-3 rounded-md border border-border p-3">
        <legend className="px-1 text-sm font-medium">Credencial</legend>
        <div className="flex gap-4 text-sm">
          {(["nueva", "existente", "ninguna"] as ModoCredencial[]).map((m) => (
            <label key={m} className="flex items-center gap-1">
              <input type="radio" name="modo-credencial" checked={modo === m} onChange={() => setModo(m)} />
              {m === "nueva" ? "Nueva" : m === "existente" ? "Usar una existente" : "Sin credencial"}
            </label>
          ))}
        </div>
        {modo === "existente" && (
          <select className={inputCls} value={idCredencial ?? ""} required
            onChange={(e) => setIdCredencial(e.target.value ? Number(e.target.value) : null)}>
            <option value="">Elegir…</option>
            {(credenciales.data ?? []).map((c) => (
              <option key={c.idCredencial} value={c.idCredencial}>
                {c.nombre}{c.usuario ? ` (${c.usuario})` : ""}
              </option>
            ))}
          </select>
        )}
        {modo === "nueva" && <CredencialForm value={nueva} onChange={setNueva} />}
      </fieldset>

      {error && <p className="text-sm text-red-700">{error}</p>}
      <div className="flex gap-2">
        <button type="submit" disabled={enviando}
          className="rounded-md bg-finance px-4 py-1.5 text-sm font-medium text-white disabled:opacity-50">
          {enviando ? "Guardando…" : "Guardar"}
        </button>
        <button type="button" onClick={onCancel} className="rounded-md border border-border px-4 py-1.5 text-sm">
          Cancelar
        </button>
      </div>
    </form>
  );
}
