import { agruparImputacion, cantidadFormateada, type FilaResumen } from "./agrupacionImputacion";

export type { FilaResumen } from "./agrupacionImputacion";

const pesos = (importe: number) => `${importe.toLocaleString("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ARS`;

export function ResumenImputacion({ filas }: { filas: FilaResumen[] }) {
  if (filas.length === 0) return <p className="text-sm text-ink-secondary">Sin imputaciones para resumir.</p>;

  return (
    <section aria-label="Resumen por cultivo y campaña" className="space-y-2">
      <h3 className="text-sm font-semibold">Resumen por cultivo y campaña</h3>
      {agruparImputacion(filas).map((grupo) => (
        <details key={grupo.clave} className="rounded-md border border-border p-3">
          <summary className="cursor-pointer text-sm font-medium">
            {grupo.destino} <span className="ml-3 tabular-nums">{pesos(grupo.importe)}</span>
          </summary>
          <ul className="mt-3 space-y-1 text-sm text-ink-secondary">
            {grupo.cantidades.map((cantidad) => (
              <li key={cantidad.clave}>{cantidad.producto}: {cantidadFormateada(cantidad)}</li>
            ))}
          </ul>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-ink-secondary">
                <tr>
                  <th className="px-2 py-2">Insumo / servicio</th>
                  <th className="px-2 py-2">Lote</th>
                  <th className="px-2 py-2 text-right">Cantidad</th>
                  <th className="px-2 py-2 text-right">Importe (ARS)</th>
                  <th className="px-2 py-2">Estado</th>
                </tr>
              </thead>
              <tbody>
                {grupo.filas.map((fila) => (
                  <tr key={fila.idPropuesta} className="border-t border-border">
                    <td className="px-2 py-2">{fila.producto}</td>
                    <td className="px-2 py-2">{fila.lote || "—"}</td>
                    <td className="whitespace-nowrap px-2 py-2 text-right tabular-nums">{cantidadFormateada(fila)}</td>
                    <td className="whitespace-nowrap px-2 py-2 text-right tabular-nums">{pesos(fila.importe)}</td>
                    <td className="px-2 py-2">{fila.estado === "RequiereIntervencion" ? "Requiere intervención" : fila.estado}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      ))}
    </section>
  );
}

