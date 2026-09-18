import Link from "next/link";

import { StatusBadge } from "@/components/ui/StatusBadge";
import type { Origen } from "@/services/cuentasCorrientesApi";

const MEDIO_LABEL: Record<string, string> = {
  bna: "Banco Nación",
  galicia: "Galicia",
  efectivo: "Efectivo",
  valores_recibidos: "Valores recibidos",
};

// El enum `medio` de cuentas corrientes usa guion bajo
// (data-model.md de specs/004), pero la ruta de Tesorería usa guion medio
// (`Medio` en tesoreriaApi.ts) — mapeo explícito para el link bidireccional.
const MEDIO_TO_TESORERIA_SLUG: Record<string, string> = {
  bna: "bna",
  galicia: "galicia",
  efectivo: "efectivo",
  valores_recibidos: "valores-recibidos",
};

/**
 * Renderiza los 9 estados de `origen` de forma explícita (004 US2:
 * FR-006, FR-007, FR-008; 005 US5: FR-005, FR-006). MUST NOT mostrar ni
 * derivar imputación (FR-007/FR-009). `fuera_de_alcance`/`no_disponible`
 * se distinguen visualmente de un origen resuelto con `StatusBadge`
 * neutral — para no sugerir trazabilidad donde no la hay (Principio IV,
 * design/agroux-frontend-redesign.md §5.3/§6).
 *
 * Vínculos bidireccionales (design/erp-module-architecture.md §3.1, 3.3,
 * 3.4, 3.6, 3.7, 2026-09-17): cada tipo resuelto navega al registro real
 * en su módulo — vía `?highlight=` cuando el módulo no tiene una ruta de
 * detalle propia por id (Tesorería/Impuestos/Remuneraciones/
 * Arrendamientos/Ventas de Hacienda son listados, no rutas `/[id]`).
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
        <Link
          href={
            origen.medio && origen.idMovimiento != null
              ? `/finanzas/tesoreria?medio=${MEDIO_TO_TESORERIA_SLUG[origen.medio] ?? origen.medio}&highlight=${origen.idMovimiento}`
              : "#"
          }
          className="text-finance underline"
        >
          Tesorería · {origen.medio ? (MEDIO_LABEL[origen.medio] ?? origen.medio) : "—"}
          {origen.fecha ? ` · ${origen.fecha}` : ""}
        </Link>
      );
    case "impuesto":
      return (
        <Link
          href={origen.idImpuesto != null ? `/finanzas/impuestos?highlight=${origen.idImpuesto}` : "#"}
          className="text-finance underline"
        >
          Impuesto · {origen.tipoImpuesto ?? "—"}
        </Link>
      );
    case "retencion":
      return (
        <Link
          href={
            origen.idRetencion != null
              ? `/finanzas/impuestos?tab=retenciones&highlight=${origen.idRetencion}`
              : "#"
          }
          className="text-finance underline"
        >
          Retención · {origen.numeroCertificado ?? "—"}
        </Link>
      );
    case "remuneracion":
      return (
        <Link
          href={
            origen.idSalario != null ? `/personal/remuneraciones?highlight=${origen.idSalario}` : "#"
          }
          className="text-finance underline"
        >
          Liquidación · {origen.empleado ?? "—"}
          {origen.periodoLiquidado ? ` · ${origen.periodoLiquidado}` : ""}
        </Link>
      );
    case "arrendamiento":
      return (
        <Link
          href={
            origen.idAlquiler != null
              ? `/finanzas/arrendamientos?highlight=${origen.idAlquiler}`
              : "#"
          }
          className="text-finance underline"
        >
          Arrendamiento · {origen.contacto ?? "—"}
        </Link>
      );
    case "venta_hacienda":
      return (
        <Link
          href={
            origen.idRetencion != null
              ? `/finanzas/impuestos?tab=retenciones-venta-hacienda&highlight=${origen.idRetencion}`
              : "#"
          }
          className="text-finance underline"
          title="Referencia a la retención — no hay clave confiable hacia la venta específica"
        >
          Retención venta de hacienda · {origen.numeroDocumento ?? "—"}
        </Link>
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
