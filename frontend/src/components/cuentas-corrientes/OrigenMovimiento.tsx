import Link from "next/link";

import type { Origen } from "@/services/cuentasCorrientesApi";

const MEDIO_LABEL: Record<string, string> = {
  bna: "Banco Nación",
  galicia: "Galicia",
  efectivo: "Efectivo",
  valores_recibidos: "Valores recibidos",
};

/**
 * Renderiza los 4 estados de `origen` de forma explícita (US2: FR-006,
 * FR-007, FR-008). MUST NOT mostrar ni derivar imputación (FR-009).
 */
export function OrigenMovimiento({ origen }: { origen: Origen }) {
  switch (origen.tipo) {
    case "compra":
      return (
        <Link
          href={origen.idCompra != null ? `/compras/${origen.idCompra}` : "#"}
          className="text-blue-700 underline"
        >
          Compra {origen.numeroDocumento ?? "—"}
          {origen.proveedor ? ` · ${origen.proveedor}` : ""}
        </Link>
      );
    case "tesoreria":
      return (
        <span className="text-slate-700">
          Tesorería · {origen.medio ? (MEDIO_LABEL[origen.medio] ?? origen.medio) : "—"}
          {origen.fecha ? ` · ${origen.fecha}` : ""}
        </span>
      );
    case "fuera_de_alcance":
      return (
        <span className="text-slate-500" title="Fuera del alcance de este sistema">
          {origen.origenTipo ?? "Fuera de alcance"}
        </span>
      );
    case "no_disponible":
    default:
      return (
        <span className="text-slate-400 italic">
          No disponible{origen.motivo ? ` (${origen.motivo})` : ""}
        </span>
      );
  }
}
