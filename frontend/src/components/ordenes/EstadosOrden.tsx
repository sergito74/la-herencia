"use client";

import { StatusBadge, type BadgeTone } from "@/components/ui/StatusBadge";
import type { EstadoOrden } from "@/services/ordenesApi";

const TONO: Record<EstadoOrden, BadgeTone> = {
  Planificada: "warning",
  Ejecutada: "success",
  Anulada: "danger",
};

export function BadgeEstadoOrden({ estado }: { estado: EstadoOrden }) {
  return <StatusBadge label={estado} tone={TONO[estado]} />;
}
