"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { useAuth } from "@/components/auth/AuthContext";
import { CompraForm } from "@/components/compras/CompraForm";
import { compraDetalleAInput } from "@/components/compras/compraDetalleAInput";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatFecha, formatMoneda } from "@/lib/format";
import { fetchCompraDetalle, urlDocumentoLocal } from "@/services/comprasApi";
import { getNuevos, marcarNuevoRevisado, type DocumentoNuevo } from "@/services/documentosNuevosApi";

/** Compra ya cargada sola: se revisa en el mismo formulario de edición. */
function EdicionCargada({ d, alGuardar }: { d: DocumentoNuevo; alGuardar: () => void }) {
  const idCompra = d.idRegistro as number;
  const q = useQuery({ queryKey: ["compra-detalle-edicion", idCompra], queryFn: () => fetchCompraDetalle(idCompra) });
  if (q.isLoading) return <LoadingState />;
  if (q.isError || !q.data) return <ErrorState message="No se pudo abrir la compra." onRetry={() => q.refetch()} />;
  return (
    <CompraForm mode="edicion" idCompra={idCompra} initial={compraDetalleAInput(q.data, idCompra)}
      proveedorNombreInicial={q.data.proveedor?.razonSocial ?? null} alGuardar={alGuardar} />
  );
}

/** Revisión de Compras nuevas (043) en el formulario de carga: lo cargado solo se abre en edición y lo que
 * falta cargar se abre como alta con los datos leídos y el archivo ya puesto. Guardar lo marca como revisado. */
export function RevisionComprasEnFormulario() {
  const { usuario } = useAuth();
  const qc = useQueryClient();
  const [abierto, setAbierto] = useState<number | null>(null);
  const q = useQuery({ queryKey: ["documentos-nuevos", "lista", "compras"], queryFn: () => getNuevos("compras") });
  const revisar = useMutation({
    mutationFn: (id: number) => marcarNuevoRevisado(id),
    onSuccess: () => { setAbierto(null); qc.invalidateQueries({ queryKey: ["documentos-nuevos"] }); },
  });
  const items = q.data?.items ?? [];
  if (q.isError) return <p className="text-sm text-red-700">No se pudieron leer las compras nuevas: {q.error.message}</p>;
  if (q.isLoading) return <LoadingState />;
  if (items.length === 0) return <p className="text-sm text-ink-secondary">No hay compras nuevas para revisar.</p>;
  const d = items.find((x) => x.idDocumentoNuevo === abierto) ?? items[0];
  const admin = usuario?.rol === "Administrador";

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-base font-semibold">Compras nuevas para revisar ({q.data?.total ?? items.length})</h2>
        <p className="text-xs text-ink-secondary">Revisá contacto, imputación e importes y guardá: queda revisada.</p>
      </div>
      <div className="flex flex-wrap gap-1">
        {items.map((x) => (
          <button key={x.idDocumentoNuevo} type="button" onClick={() => setAbierto(x.idDocumentoNuevo)}
            className={`rounded-sm border px-2 py-0.5 text-xs ${x.idDocumentoNuevo === d.idDocumentoNuevo
              ? "border-finance bg-finance-light text-finance" : "border-border text-ink-secondary"}`}>
            {x.contacto ?? x.archivo} {x.fecha ? formatFecha(x.fecha) : ""}
            {x.idRegistro ? "" : " · a cargar"}
          </button>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <span>
          <strong>{d.contacto ?? "Emisor sin identificar"}</strong> {d.tipo} {d.numero ?? ""}
          {d.total != null && ` · ${formatMoneda(d.total, "Pesos")}`}
        </span>
        <a href={urlDocumentoLocal(d.ruta)} target="_blank" rel="noreferrer" className="text-finance hover:underline">
          Ver archivo
        </a>
        {d.motivo && !d.idRegistro && <span className="text-xs text-amber-900">{d.motivo}</span>}
        {admin && (
          <button type="button" disabled={revisar.isPending} onClick={() => revisar.mutate(d.idDocumentoNuevo)}
            title="Marcarla como revisada sin cambios"
            className="ml-auto rounded-md border border-border px-3 py-1 text-xs disabled:opacity-40">
            Está bien, revisada
          </button>
        )}
      </div>
      {d.idRegistro ? (
        <EdicionCargada key={d.idDocumentoNuevo} d={d} alGuardar={() => revisar.mutate(d.idDocumentoNuevo)} />
      ) : (
        <CompraForm key={d.idDocumentoNuevo} mode="alta" alGuardar={() => revisar.mutate(d.idDocumentoNuevo)}
          prefill={{
            idContacto: d.idContacto, proveedorNombre: d.contacto, fecha: d.fecha ?? undefined,
            numeroDocumento: d.numero ?? undefined, importe: d.total ?? undefined, documentoOriginal: d.ruta,
          }} />
      )}
    </section>
  );
}
