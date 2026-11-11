"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { MoneyInput } from "@/components/ui/MoneyInput";
import { formatFecha, formatMoneda } from "@/lib/format";
import { fetchComprobantesPendientes, registrarPagoProveedor, type ComprobantePendiente } from "@/services/cuentasSociosApi";

const input = "mt-1 block w-full rounded-sm border border-border bg-surface px-3 py-2 text-sm";
const MEDIOS = ["Banco Galicia", "ICBC", "Supervielle", "Banco Nación", "Mercado Pago", "Tarjeta de crédito", "Efectivo", "Otro"];
const clave = (c: ComprobantePendiente) => `${c.tipoDocumento}-${c.idDocumento}`;
const redondo = (n: number) => Math.round(n * 100) / 100;

/** Gasto de Giamigli pagado por un socio (o el Condominio) desde su cuenta personal (11/11/2026): en un solo paso queda a
 * favor del socio, cancela la deuda en la cuenta del proveedor y, si se eligen, imputa los comprobantes que se pagan. */
export function PagoProveedorSocioForm({ idSocio, onListo }: { idSocio: number; onListo: () => void }) {
  const cache = useQueryClient();
  const [idContacto, setIdContacto] = useState<number | null>(null);
  const [proveedor, setProveedor] = useState<string | null>(null);
  const [fecha, setFecha] = useState(new Date().toISOString().slice(0, 10));
  const [importe, setImporte] = useState(0);
  const [importeManual, setImporteManual] = useState(false);
  const [medio, setMedio] = useState(MEDIOS[0]);
  const [motivo, setMotivo] = useState("");
  const [elegidos, setElegidos] = useState<Record<string, number>>({});

  const pendientes = useQuery({
    queryKey: ["comprobantes-pendientes-socio", idContacto],
    queryFn: () => fetchComprobantesPendientes(idContacto as number),
    enabled: idContacto !== null,
  });
  const aplicado = redondo(Object.values(elegidos).reduce((a, x) => a + x, 0));

  function actualizar(nuevos: Record<string, number>) {
    setElegidos(nuevos);
    if (!importeManual) setImporte(redondo(Object.values(nuevos).reduce((a, x) => a + x, 0)));
  }
  function tildar(c: ComprobantePendiente, si: boolean) {
    const n = { ...elegidos };
    if (si) {
      n[clave(c)] = c.saldo;
      if (!motivo.trim()) setMotivo(`${c.descripcion} ${c.numero}`.trim());
    } else delete n[clave(c)];
    actualizar(n);
  }

  const guardar = useMutation({
    mutationFn: () => {
      if (!idContacto) throw new Error("Elegí a quién se le pagó.");
      if (importe <= 0) throw new Error("El importe debe ser mayor a $0.");
      if (!motivo.trim()) throw new Error("Escribí el concepto (ej. Autónomos Lucy 10/2026).");
      if (aplicado - importe > 0.005) throw new Error("Lo aplicado a los comprobantes supera el importe pagado.");
      const comprobantes = (pendientes.data ?? []).filter((c) => elegidos[clave(c)] > 0)
        .map((c) => ({ tipoDocumento: c.tipoDocumento, idDocumento: c.idDocumento, importe: elegidos[clave(c)] }));
      return registrarPagoProveedor(idSocio, { idContacto, importe, fecha, medio, motivo, comprobantes });
    },
    onSuccess: async () => {
      await cache.invalidateQueries({ queryKey: ["cuenta-socio", idSocio] });
      await cache.invalidateQueries({ queryKey: ["cuentas-socios"] });
      await cache.invalidateQueries({ queryKey: ["facturas-a-pagar"] });
      await cache.invalidateQueries({ queryKey: ["comprobantes-pendientes-socio"] });
      onListo();
    },
  });

  return (
    <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); guardar.mutate(); }}>
      <p className="text-sm text-slate-600">Queda a favor del socio y descuenta lo que Giamigli le debe a quien se le pagó.</p>
      <ContactoSelect label="A quién se le pagó" value={idContacto} razonSocial={proveedor}
        onChange={(id, r) => { setIdContacto(id); setProveedor(r); setElegidos({}); if (!importeManual) setImporte(0); }}
        placeholder="Buscar proveedor u organismo…" />

      {idContacto !== null && (
        <section className="rounded-sm border border-border">
          <h3 className="border-b border-border bg-surface-sunken px-3 py-2 text-sm font-medium">Qué comprobantes se pagan</h3>
          {pendientes.isLoading && <p className="p-3 text-sm text-slate-600">Buscando comprobantes…</p>}
          {pendientes.isError && <p role="alert" className="p-3 text-sm text-status-danger">No se pudieron traer los comprobantes.</p>}
          {pendientes.data?.length === 0 && <p className="p-3 text-sm text-slate-600">No tiene comprobantes impagos. Podés guardar el pago igual: queda a cuenta.</p>}
          {!!pendientes.data?.length && (
            <div className="max-h-72 overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-surface text-left text-xs text-slate-600">
                  <tr><th className="p-2" /><th className="p-2">Fecha</th><th className="p-2">Comprobante</th><th className="p-2 text-right">Total</th><th className="p-2 text-right">Saldo</th><th className="p-2 text-right">Aplicar</th></tr>
                </thead>
                <tbody>
                  {pendientes.data.map((c) => {
                    const k = clave(c);
                    const tildado = k in elegidos;
                    return (
                      <tr key={k} className={`border-t border-border ${tildado ? "bg-amber-50" : ""}`}>
                        <td className="p-2"><input type="checkbox" aria-label={`Pagar ${c.descripcion} ${c.numero}`} checked={tildado} onChange={(e) => tildar(c, e.target.checked)} /></td>
                        <td className="whitespace-nowrap p-2">{formatFecha(c.fecha)}</td>
                        <td className="p-2">{c.descripcion} {c.numero}
                          {c.posiblePagoSocio && <span className="block text-[11px] text-amber-800">Hay un pago de socio por este mismo importe sin comprobante: puede que ya esté pagado.</span>}</td>
                        <td className="whitespace-nowrap p-2 text-right">{formatMoneda(c.total)}</td>
                        <td className="whitespace-nowrap p-2 text-right">{formatMoneda(c.saldo)}</td>
                        <td className="p-2 text-right">{tildado && (
                          <MoneyInput className="w-32 rounded-sm border border-border bg-surface px-2 py-1 text-right" moneda="Pesos" value={elegidos[k]}
                            onChange={(v) => actualizar({ ...elegidos, [k]: Math.min(v, c.saldo) })} />)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          {aplicado > 0 && <p className="border-t border-border px-3 py-2 text-right text-sm">Aplicado a comprobantes: <strong>{formatMoneda(aplicado)}</strong>
            {importe - aplicado > 0.005 && <> · queda a cuenta {formatMoneda(redondo(importe - aplicado))}</>}</p>}
        </section>
      )}

      <label className="block text-sm">Concepto<input className={input} value={motivo} onChange={(e) => setMotivo(e.target.value)} placeholder="Ej: Autónomos Lucy 10/2026" /></label>
      <div className="grid grid-cols-2 gap-3">
        <label className="text-sm">Fecha del pago<input type="date" required className={input} value={fecha} onChange={(e) => setFecha(e.target.value)} /></label>
        <label className="text-sm">Importe pagado<MoneyInput className={input} moneda="Pesos" value={importe} onChange={(v) => { setImporte(v); setImporteManual(true); }} /></label>
      </div>
      <label className="block text-sm">Pagado desde<select className={input} value={medio} onChange={(e) => setMedio(e.target.value)}>
        {MEDIOS.map((m) => <option key={m} value={m}>{m}</option>)}</select></label>
      {guardar.error && <p role="alert" className="text-sm text-status-danger">{guardar.error.message || "No se pudo guardar."}</p>}
      <div className="flex justify-end">
        <button type="submit" disabled={guardar.isPending} className="rounded-sm bg-agro px-4 py-2 text-sm text-white disabled:opacity-50">{guardar.isPending ? "Guardando…" : "Guardar pago"}</button>
      </div>
    </form>
  );
}
