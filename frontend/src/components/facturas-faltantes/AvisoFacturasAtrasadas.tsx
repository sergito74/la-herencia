"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { fetchResumenMensual } from "@/services/facturasFaltantesApi";

/** Aviso de cierre de mes (044, rutina 043): desde el día 5, facturas atrasadas del mes anterior. */
export function AvisoFacturasAtrasadas() {
  const q = useQuery({ queryKey: ["facturas-faltantes", "resumen-mensual"], queryFn: fetchResumenMensual, staleTime: 10 * 60_000 });
  if (!q.data?.mostrar) return null;
  const r = q.data;
  return (
    <p role="status" className="rounded-md border border-border bg-status-warning/10 px-3 py-2 text-sm">
      Cierre de {r.mes}: {r.atrasadas === 1 ? "falta 1 factura" : `faltan ${r.atrasadas} facturas`} de proveedores que facturan seguido
      ({r.proveedores.join(", ")}). <Link className="underline" href="/finanzas/facturas-esperadas">Ver facturas esperadas</Link>
    </p>
  );
}
