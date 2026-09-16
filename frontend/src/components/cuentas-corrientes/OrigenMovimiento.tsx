import Link from "next/link";

import { StatusBadge } from "@/components/ui/StatusBadge";
import type { Origen } from "@/services/cuentasCorrientesApi";

const MEDIO_LABEL: Record<string, string> = {
  bna: "Banco Nación",
  galicia: "Galicia",
  efectivo: "Efectivo",
  valores_recibidos: "Valores recibidos",
};

/**
 * Renderiza los 9 estados de `origen` de forma explícita (004 US2:
 * FR-006, FR-007, FR-008; 005 US5: FR-005, FR-006). MUST NOT mostrar ni
 * derivar imputación (FR-007/FR-009). `fuera_de_alcance`/`no_disponible`
 * se distinguen visualmente de un origen resuelto con `StatusBadge`
 * neutral — para no sugerir trazabilidad donde no la hay (Principio IV,
 * design/agroux-frontend-redesign.md §5.3/§6).
 */
export function OrigenMovimiento({ origen }: { origen: Origen }) {
  switch (origen.tipo) {
    case "compra":
      return (
        <Link
          href={origen.idCompra != null ? `/compras/${origen.idCompra}` : "#"}
          className="text-finance underline"
        >
          Compra {origen.numeroDocumento ?? "—"}
          {origen.proveedor ? ` · ${origen.proveedor}` : ""}
        </Link>
      );
    case "tesoreria":
      return (
        <span className="text-ink-primary">
          Tesorería · {origen.medio ? (MEDIO_LABEL[origen.medio] ?? origen.medio) : "—"}
          {origen.fecha ? ` · ${origen.fecha}` : ""}
        </span>
      );
    case "impuesto":
      return <span className="text-ink-primary">Impuesto · {origen.tipoImpuesto ?? "—"}</span>;
    case "retencion":
      return (
        <span className="text-ink-primary">Retención · {origen.numeroCertificado ?? "—"}</span>
      );
    case "remuneracion":
      return (
        <span className="text-ink-primary">
          Liquidación · {origen.empleado ?? "—"}
          {origen.periodoLiquidado ? ` · ${origen.periodoLiquidado}` : ""}
        </span>
      );
    case "arrendamiento":
      return <span className="text-ink-primary">Arrendamiento · {origen.contacto ?? "—"}</span>;
    case "venta_hacienda":
      return (
        <span className="text-ink-primary">
          Retención venta de hacienda · {origen.numeroDocumento ?? "—"}
        </span>
      );
    case "fuera_de_alcance":
      return (
        <span title="Fuera del alcance de este sistema">
          <StatusBadge label={origen.origenTipo ?? "Fuera de alcance"} tone="neutral" />
        </span>
      );
    case "no_disponible":
    default:
      return (
        <span className="italic text-ink-muted">
          No disponible{origen.motivo ? ` (${origen.motivo})` : ""}
        </span>
      );
  }
}
