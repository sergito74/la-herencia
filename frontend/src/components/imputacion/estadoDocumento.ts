import type { BadgeTone } from "@/components/ui/StatusBadge";
import type { EstadoDoc } from "@/services/imputacionDocumentosApi";

/** Rojo nunca: lo que espera una decisión es ámbar (auditoría de diseño 18/11/2026). */
export const TONO_ESTADO: Record<EstadoDoc, BadgeTone> = {
  decision: "warning", revisar: "warning", pendiente: "warning", aprobado: "success",
};
