import { formatFecha, formatNumero } from "@/lib/format";
import type { OrdenDetalle } from "@/services/ordenesApi";

/**
 * Documento imprimible del Formulario de Retiro (FR-008), con el formato de la planilla
 * que se usaba en el campo (Retiro_151): hoja apaisada, Ing. Activo · Marca Comercial ·
 * Cantidad · Unidad, ordenado por principio activo. Encabezado con membrete, datos de la
 * orden y lotes; pie con firmas de entrega y retiro.
 */
export function FormularioRetiroDocumento({ orden }: { orden: OrdenDetalle }) {
  const formulario = orden.formularioRetiro;
  if (!formulario) return null;

  const renglones = [...orden.insumos].sort(
    (a, b) =>
      (a.ingredienteActivo ?? "").trim().localeCompare((b.ingredienteActivo ?? "").trim(), "es") ||
      (a.producto ?? "").localeCompare(b.producto ?? "", "es")
  );

  // Cultivo/campaña -> lotes con su superficie (sin repetir lotes entre insumos).
  const destinos = new Map<string, Map<string, number>>();
  for (const r of orden.insumos) {
    for (const d of r.distribuciones) {
      if (!d.aplicar || d.cantidadAsignada <= 0) continue;
      const clave = [d.cultivo, d.campania].filter(Boolean).join(" ");
      const lotes = destinos.get(clave) ?? new Map<string, number>();
      lotes.set(d.lote ?? String(d.idLote), d.superficie);
      destinos.set(clave, lotes);
    }
  }

  const dato = (titulo: string, valor: React.ReactNode) => (
    <div>
      <dt className="text-[10px] font-medium uppercase tracking-wide text-ink-secondary">{titulo}</dt>
      <dd className="text-sm">{valor}</dd>
    </div>
  );

  return (
    <article className="mx-auto w-full max-w-[277mm] bg-white p-6 text-ink-primary print:p-0 print:text-[13px]">
      {/* Encabezado: membrete · título · número de formulario */}
      <header className="grid grid-cols-[1fr_auto_1fr] items-center gap-4 border-b-2 border-ink-primary pb-3">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-md bg-agro text-lg font-semibold text-white print:[-webkit-print-color-adjust:exact] print:[print-color-adjust:exact]">
            LH
          </span>
          <div className="leading-tight">
            <p className="text-lg font-semibold">La Herencia</p>
            <p className="text-xs text-ink-secondary">Producción agrícola · Depósito de insumos</p>
          </div>
        </div>
        <div className="text-center">
          <h1 className="text-xl font-bold tracking-wide">RETIRO DE AGROQUÍMICOS</h1>
          <p className="text-xs text-ink-secondary">Formulario de retiro de insumos para aplicación</p>
        </div>
        <div className="justify-self-end rounded border border-ink-primary px-3 py-1 print:py-0.5 text-right">
          <p className="text-[10px] font-medium uppercase tracking-wide text-ink-secondary">Formulario N°</p>
          <p className="font-data text-2xl font-bold leading-none">{formulario.idFormularioRetiro}</p>
          <p className="mt-0.5 text-xs">Emitido {formatFecha(formulario.fechaEmision)}</p>
        </div>
      </header>

      {/* Datos de la orden */}
      <dl className="mt-3 grid grid-cols-4 gap-x-6 gap-y-2 rounded border border-border px-3 py-2">
        {dato("Orden de trabajo", <span className="font-data font-semibold">N° {orden.idOrden}</span>)}
        {dato("Fecha", formatFecha(orden.fechaPedido))}
        {dato("Labor", orden.tipoLabor ?? "—")}
        {dato("Contratista", orden.contratista ?? "Maquinaria propia")}
        <div className="col-span-4">
          {dato(
            "Cultivos y lotes",
            destinos.size === 0
              ? "—"
              : [...destinos.entries()].map(([cultivo, lotes]) => (
                  <span key={cultivo} className="mr-4 inline-block">
                    <span className="font-medium">{cultivo}:</span> {[...lotes.keys()].join(", ")} (
                    {formatNumero([...lotes.values()].reduce((a, b) => a + b, 0), { min: 0, max: 1 })} ha)
                  </span>
                ))
          )}
        </div>
      </dl>

      {/* Detalle: mismo formato que la planilla de retiro del campo */}
      <table className="mt-4 w-full border-collapse text-sm">
        <thead>
          <tr className="border-y border-ink-primary text-left">
            <th className="w-8 py-1 print:py-0.5 pr-2 text-right font-semibold">#</th>
            <th className="py-1 print:py-0.5 pr-4 font-semibold">Ing. Activo</th>
            <th className="py-1 print:py-0.5 pr-4 font-semibold">Marca Comercial</th>
            <th className="w-28 py-1 print:py-0.5 pr-4 text-right font-semibold">Cantidad</th>
            <th className="w-20 py-1 print:py-0.5 pr-4 font-semibold">Unidad</th>
            <th className="w-24 py-1 print:py-0.5 text-center font-semibold">Control</th>
          </tr>
        </thead>
        <tbody>
          {renglones.map((r, i) => (
            <tr key={r.idOrdenInsumo} className="border-b border-border">
              <td className="py-1 print:py-0.5 pr-2 text-right font-data text-ink-secondary">{i + 1}</td>
              <td className="py-1 print:py-0.5 pr-4">{r.ingredienteActivo?.trim() || "—"}</td>
              <td className="py-1 print:py-0.5 pr-4 font-medium">{r.producto ?? r.idProducto}</td>
              <td className="py-1 print:py-0.5 pr-4 text-right font-data">{formatNumero(r.cantidadTotal, { min: 1, max: 3 })}</td>
              <td className="py-1 print:py-0.5 pr-4">{r.unidad}</td>
              <td className="py-1 print:py-0.5 text-center">
                <span className="inline-block h-4 w-4 border border-ink-secondary align-middle" />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {orden.observaciones && (
        <p className="mt-3 text-sm">
          <span className="font-medium">Observaciones:</span> {orden.observaciones}
        </p>
      )}

      {/* Firmas */}
      <footer className="mt-12 grid grid-cols-3 print:mt-10 gap-10 text-center text-xs break-inside-avoid">
        {["Entregó (encargado de depósito)", "Retiró (contratista / operario)", "Fecha y hora de retiro"].map((t) => (
          <div key={t}>
            <div className="border-t border-ink-primary pt-1">{t}</div>
          </div>
        ))}
      </footer>
      <p className="mt-6 text-right text-[10px] text-ink-secondary">
        La Herencia · Orden N° {orden.idOrden} · Formulario N° {formulario.idFormularioRetiro}
      </p>
    </article>
  );
}
