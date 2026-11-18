import { apiGet } from "./apiClient";

/** Inicio "Para hacer hoy" (spec 051). */
export interface Pendiente {
  clave: string;
  cantidad?: number;
  texto: string;
  destino: string;
  importe?: number | null;
  detalle?: string | null;
  vencidas?: number | null;
  error?: boolean;
}
export interface ResumenInicio {
  listo: boolean;
  actualizando: boolean;
  calculado?: string;
  pendientes?: Pendiente[];
  indicadores?: {
    bancos?: { total?: number; cuentas?: Record<string, { saldo: number; fecha: string }>; error?: boolean };
    deuda?: { pesos?: number; dolares?: number; proveedores?: number; error?: boolean };
    stock?: { valor?: number; productos?: number; error?: boolean };
    cajas?: { pesos?: number; dolares?: number; error?: boolean };
  };
  flujo?: { periodo: string; neto: number }[] | { error: boolean };
  campania?: { nombre?: string; cultivos?: { cultivo: string; ha: number }[]; ordenes?: { id: number; fecha: string; estado: string; labor: string | null }[]; error?: boolean };
}
export const fetchInicio = (actualizar = false) => apiGet<ResumenInicio>("/api/inicio", actualizar ? { actualizar: "true" } : undefined);
