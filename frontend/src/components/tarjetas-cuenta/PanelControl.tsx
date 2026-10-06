"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatFecha, formatMoneda } from "@/lib/format";
import { fetchControl, fetchResumenTarjetas, urlExportarControl, type CategoriaControl } from "@/services/tarjetasCuentaApi";

const NOMBRES: Record<CategoriaControl, string> = {
  "pago-en-proveedor": "Pago de tarjeta cargado a un proveedor",
  "movimiento-sin-resumen": "Movimiento de la tarjeta sin resumen",
  "pago-sin-origen-o-importe": "Pago sin movimiento o con otro importe",
  "resumen-con-pendiente": "Resumen con saldo pendiente",
  "devolucion-sin-cruzar": "Devolución sin cruzar con su débito",
  "saldo-inicial-con-pagos": "Saldo inicial con pagos",
  "tarjeta-sin-contacto": "Tarjeta sin cuenta asociada",
  "consumo-sin-vinculo-con-deuda-abierta": "Consumo sin vincular y el proveedor tiene deuda",
  "consumo-sin-proveedor": "Consumo sin proveedor",
  "diferencia-contrapartida": "Saldo distinto al del módulo de tarjetas",
  "continuidad-de-resumenes": "Resúmenes sin continuidad",
  "indicios-de-otra-moneda": "Posible importe en otra moneda",
};

/** Control de integridad de las cuentas de tarjetas (034, FR-010/FR-011). Solo informa: no corrige nada. */
export function PanelControl() {
  const [idTarjeta, setIdTarjeta] = useState<number | undefined>();
  const [categoria, setCategoria] = useState<CategoriaControl | undefined>();
  const filtros = { idTarjeta, categoria };
  const tarjetas = useQuery({ queryKey: ["tarjetas-cuenta-resumen"], queryFn: () => fetchResumenTarjetas() });
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["tarjetas-cuenta-control", idTarjeta, categoria],
    queryFn: () => fetchControl(filtros),
  });

  if (isLoading) return <LoadingState />;
  if (isError || !data) return <ErrorState message="No se pudo cargar el control." onRetry={() => refetch()} />;

  const resumen = Object.entries(data.resumenPorCategoria) as [CategoriaControl, number][];
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-3 text-xs">
        <label className="flex flex-col">
          Tarjeta
          <select
            value={idTarjeta ?? ""}
            onChange={(e) => setIdTarjeta(e.target.value ? Number(e.target.value) : undefined)}
            className="rounded border border-line px-2 py-1"
          >
            <option value="">Todas</option>
            {tarjetas.data?.tarjetas.map((t) => (
              <option key={t.idTarjeta} value={t.idTarjeta}>{t.tarjeta}</option>
            ))}
          </select>
        </label>
        <label className="flex flex-col">
          Categoría
          <select
            value={categoria ?? ""}
            onChange={(e) => setCategoria((e.target.value || undefined) as CategoriaControl | undefined)}
            className="rounded border border-line px-2 py-1"
          >
            <option value="">Todas</option>
            {(Object.keys(NOMBRES) as CategoriaControl[]).map((c) => (
              <option key={c} value={c}>{NOMBRES[c]}</option>
            ))}
          </select>
        </label>
        <a className="text-finance underline" href={urlExportarControl(filtros)}>Exportar a Excel</a>
      </div>

      <ul className="flex flex-wrap gap-2 text-xs">
        {resumen.length === 0 && <li className="text-status-success">Sin hallazgos.</li>}
        {resumen.map(([c, n]) => (
          <li key={c} className="rounded border border-line px-2 py-1">{NOMBRES[c] ?? c}: <b>{n}</b></li>
        ))}
      </ul>

      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-ink-secondary">
            <th className="py-1">Categoría</th><th>Tarjeta</th><th>Fecha</th><th className="text-right">Importe</th><th>Motivo</th>
          </tr>
        </thead>
        <tbody>
          {data.hallazgos.map((h, i) => (
            <tr key={i} className="border-t border-line">
              <td className="py-1">{NOMBRES[h.categoria] ?? h.categoria}</td>
              <td>{h.tarjeta}</td>
              <td>{formatFecha(h.fecha)}</td>
              <td className="text-right">{h.importe != null ? formatMoneda(h.importe) : "—"}</td>
              <td className="text-xs">{h.motivo}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
