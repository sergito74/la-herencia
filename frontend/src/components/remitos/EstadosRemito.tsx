"use client";

import { StatusBadge, type BadgeTone } from "@/components/ui/StatusBadge";
import {
  ETIQUETA_ESTADO_FACTURA,
  ETIQUETA_ESTADO_RENGLONES,
  type EstadoFactura,
  type EstadoRenglones,
} from "@/services/remitosApi";

const TONO_RENGLONES: Record<EstadoRenglones, BadgeTone> = {
  SinVincular: "neutral",
  Parcial: "warning",
  Completo: "success",
  ConDiferencia: "danger",
};

export function BadgeFactura({ estado, dias }: { estado: EstadoFactura; dias?: number | null }) {
  const sinFactura = estado === "SinFactura";
  const etiqueta = sinFactura && dias != null && dias > 0 ? `${ETIQUETA_ESTADO_FACTURA[estado]} · ${dias} d` : ETIQUETA_ESTADO_FACTURA[estado];
  return <StatusBadge label={etiqueta} tone={sinFactura ? (dias != null && dias > 30 ? "danger" : "warning") : "success"} />;
}

export function BadgeRenglones({ estado }: { estado: EstadoRenglones }) {
  return <StatusBadge label={ETIQUETA_ESTADO_RENGLONES[estado]} tone={TONO_RENGLONES[estado]} />;
}

/** Botón-link que descarga una planilla (.xlsx) del backend. */
export function BotonExcel({ href, titulo }: { href: string; titulo?: string }) {
  return (
    <a
      href={href}
      title={titulo ?? "Descarga una planilla con los filtros aplicados."}
      className="rounded-sm border border-finance px-4 py-2 text-sm text-finance hover:bg-finance-light"
    >
      Exportar a Excel
    </a>
  );
}
