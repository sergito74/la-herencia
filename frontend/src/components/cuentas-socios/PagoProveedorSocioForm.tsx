"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { MoneyInput } from "@/components/ui/MoneyInput";
import { ApiError } from "@/services/apiClient";
import { registrarPagoProveedor } from "@/services/cuentasSociosApi";

const input = "mt-1 block w-full rounded-sm border border-border bg-surface px-3 py-2 text-sm";
const MEDIOS = ["Banco Galicia", "ICBC", "Supervielle", "Banco Nación", "Mercado Pago", "Tarjeta de crédito", "Efectivo", "Otro"];

/** Gasto de Giamigli pagado por el socio desde su cuenta personal (11/11/2026): en un solo paso queda a favor del socio
 * y cancela la deuda en la cuenta del proveedor ("Pagó el socio"). */
export function PagoProveedorSocioForm({ idSocio, onListo }: { idSocio: number; onListo: () => void }) {
  const cache = useQueryClient();
  const [idContacto, setIdContacto] = useState<number | null>(null);
  const [proveedor, setProveedor] = useState<string | null>(null);
  const [fecha, setFecha] = useState(new Date().toISOString().slice(0, 10));
  const [importe, setImporte] = useState(0);
  const [medio, setMedio] = useState(MEDIOS[0]);
  const [motivo, setMotivo] = useState("");
  const guardar = useMutation({
    mutationFn: () => {
      if (!idContacto) throw new Error("Elegí a quién se le pagó.");
      if (importe <= 0) throw new Error("El importe debe ser mayor a $0.");
      if (!motivo.trim()) throw new Error("Escribí el concepto (ej. Autónomos Lucy 10/2026).");
      return registrarPagoProveedor(idSocio, { idContacto, importe, fecha, medio, motivo });
    },
    onSuccess: async () => {
      await cache.invalidateQueries({ queryKey: ["cuenta-socio", idSocio] });
      await cache.invalidateQueries({ queryKey: ["cuentas-socios"] });
      await cache.invalidateQueries({ queryKey: ["facturas-a-pagar"] });
      setImporte(0); setMotivo("");
      onListo();
    },
  });
  return (
    <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); guardar.mutate(); }}>
      <p className="text-sm text-slate-600">Queda a favor del socio y descuenta lo que Giamigli le debe a quien se le pagó.</p>
      <ContactoSelect label="A quién se le pagó" value={idContacto} razonSocial={proveedor}
        onChange={(id, r) => { setIdContacto(id); setProveedor(r); }} placeholder="Buscar proveedor u organismo…" />
      <label className="block text-sm">Concepto<input className={input} value={motivo} onChange={(e) => setMotivo(e.target.value)} placeholder="Ej: Autónomos Lucy 10/2026" /></label>
      <div className="grid grid-cols-2 gap-3">
        <label className="text-sm">Fecha<input type="date" required className={input} value={fecha} onChange={(e) => setFecha(e.target.value)} /></label>
        <label className="text-sm">Importe en pesos<MoneyInput className={input} moneda="Pesos" value={importe} onChange={setImporte} /></label>
      </div>
      <label className="block text-sm">Pagado desde<select className={input} value={medio} onChange={(e) => setMedio(e.target.value)}>
        {MEDIOS.map((m) => <option key={m} value={m}>{m}</option>)}</select></label>
      {guardar.error && <p role="alert" className="text-sm text-status-danger">{guardar.error instanceof ApiError || guardar.error instanceof Error ? guardar.error.message : "No se pudo guardar."}</p>}
      <div className="flex justify-end">
        <button type="submit" disabled={guardar.isPending} className="rounded-sm bg-agro px-4 py-2 text-sm text-white disabled:opacity-50">{guardar.isPending ? "Guardando…" : "Guardar pago"}</button>
      </div>
    </form>
  );
}
