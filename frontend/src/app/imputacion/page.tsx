import { redirect } from "next/navigation";

/** 18/11/2026 (auditoría de diseño): la pantalla "Automática" quedó dentro de Documentos, como el filtro "Pendientes". */
export default function ImputacionPage({ searchParams }: { searchParams: Record<string, string | undefined> }) {
  redirect(searchParams.idDetalleCompra ? "/imputacion/documentos?estado=pendiente" : "/imputacion/documentos");
}
