"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { formatFecha, formatMoneda } from "@/lib/format";
import { getFoto, getFotos, marcarFotoRevisada, type Foto } from "@/services/bovedaApi";

const moneda = (f: Foto) => (f.moneda === "USD" ? "Dolares" : "Pesos");

/** Fotos del estado de cuenta del portal contra el saldo del sistema (042, US3, T033).
 * Comparación al centavo: cualquier diferencia distinta de cero se marca. "Revisada"
 * solo indica que se vio; no crea movimientos ni ajustes. */
export function EstadoCuentaPanel({ idPortal }: { idPortal: number }) {
  const qc = useQueryClient();
  const fotos = useQuery({ queryKey: ["boveda", "fotos", idPortal], queryFn: () => getFotos(idPortal) });
  const [abierta, setAbierta] = useState<number | null>(null);
  const detalle = useQuery({
    queryKey: ["boveda", "foto", abierta],
    queryFn: () => getFoto(abierta!),
    enabled: abierta !== null,
  });
  const revisar = useMutation({
    mutationFn: ({ id, valor }: { id: number; valor: boolean }) => marcarFotoRevisada(id, valor),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["boveda"] }),
  });

  if (!fotos.data?.length) return <p className="text-sm text-ink-muted">Todavía no hay fotos del estado de cuenta.</p>;

  return (
    <div className="space-y-3">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-ink-muted">
            <th className="py-2 pr-3">Corte</th>
            <th className="py-2 pr-3 text-right">Saldo portal</th>
            <th className="py-2 pr-3 text-right">Saldo sistema</th>
            <th className="py-2 pr-3 text-right">Diferencia</th>
            <th className="py-2 pr-3" />
          </tr>
        </thead>
        <tbody>
          {fotos.data.map((f) => {
            const hayDif = f.diferencia !== null && f.diferencia !== 0;
            return (
              <tr key={f.idFoto} className="border-b border-border/60">
                <td className="py-2 pr-3">
                  {formatFecha(f.fechaCorte)} {f.moneda}
                  {!f.completa && <span className="ml-1 text-xs text-ink-muted">(incompleta: no se compara)</span>}
                </td>
                <td className="py-2 pr-3 text-right">{formatMoneda(f.saldoPortal, moneda(f))}</td>
                <td className="py-2 pr-3 text-right">{f.saldoSistema === null ? "—" : formatMoneda(f.saldoSistema, moneda(f))}</td>
                <td className={`py-2 pr-3 text-right ${hayDif ? "font-medium text-red-700" : ""}`}>
                  {f.diferencia === null ? "—" : formatMoneda(f.diferencia, moneda(f))}
                </td>
                <td className="py-2 pr-3 text-right text-xs">
                  <button type="button" className="text-finance underline" onClick={() => setAbierta(abierta === f.idFoto ? null : f.idFoto)}>
                    {abierta === f.idFoto ? "Ocultar" : "Movimientos"}
                  </button>
                  {hayDif && (
                    <label className="ml-3 inline-flex items-center gap-1">
                      <input type="checkbox" checked={f.revisada}
                        onChange={(e) => revisar.mutate({ id: f.idFoto, valor: e.target.checked })} />
                      Revisada
                    </label>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {abierta !== null && detalle.data?.movimientos && (
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border text-left text-ink-muted">
              <th className="py-1 pr-3">Fecha</th><th className="py-1 pr-3">Comprobante</th><th className="py-1 pr-3">Detalle</th>
              <th className="py-1 pr-3 text-right">Debe</th><th className="py-1 pr-3 text-right">Haber</th><th className="py-1 pr-3 text-right">Saldo</th>
            </tr>
          </thead>
          <tbody>
            {detalle.data.movimientos.map((m, i) => (
              <tr key={i} className="border-b border-border/40">
                <td className="py-1 pr-3">{formatFecha(m.fecha)}</td>
                <td className="py-1 pr-3">{m.comprobante ?? ""}</td>
                <td className="py-1 pr-3">{m.detalle ?? ""}</td>
                <td className="py-1 pr-3 text-right">{m.debe == null ? "" : formatMoneda(m.debe, moneda(detalle.data!))}</td>
                <td className="py-1 pr-3 text-right">{m.haber == null ? "" : formatMoneda(m.haber, moneda(detalle.data!))}</td>
                <td className="py-1 pr-3 text-right">{m.saldo == null ? "" : formatMoneda(m.saldo, moneda(detalle.data!))}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
