import type { ContextoComercial } from "@/services/imputacionApi";

export function EncabezadoPropuesta({ contexto }: { contexto: ContextoComercial }) {
  return (
    <header className="mb-3 rounded-md bg-surface-sunken px-3 py-2">
      <p className="text-sm text-ink-secondary">
        {contexto.tipoDocumento || "Documento"} {contexto.numeroDocumento || "Sin número"}
        {" · "}{contexto.proveedor || "Proveedor no informado"}
      </p>
      <p className="mt-1 text-xs text-ink-secondary">
        {contexto.fechaDocumento
          ? contexto.fechaDocumento.slice(0, 10).split("-").reverse().join("/")
          : "Fecha no informada"}
        {" · Moneda del documento: "}{contexto.monedaDocumento || "No informada"}
      </p>
      <h2 className="mt-2 font-medium">{contexto.producto || "Insumo o servicio sin descripción"}</h2>
    </header>
  );
}
