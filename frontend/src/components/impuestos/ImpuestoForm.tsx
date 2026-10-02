"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ArchivoVinculado } from "@/components/ui/ArchivoVinculado";
import { filterInputClass } from "@/components/ui/FilterBar";
import { MoneyInput } from "@/components/ui/MoneyInput";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { useToast } from "@/components/ui/Toast";
import { ApiError } from "@/services/apiClient";
import {
  crearImpuesto,
  editarImpuesto,
  eliminarImpuesto,
  fetchCatalogoImpuestos,
  type ImpuestoDetalle,
  type ImpuestoInput,
} from "@/services/impuestosApi";

const input = `${filterInputClass} w-full px-2 py-1.5 text-sm`;
const label = "flex flex-col gap-1 text-sm text-ink-secondary";

function mensaje(err: unknown): string {
  return err instanceof ApiError && err.message ? err.message : "No se pudo guardar. Intentá de nuevo.";
}

/**
 * Alta y edición de una boleta de impuesto (033-alta-impuestos). El tipo
 * de impuesto se elige de los que corresponden al organismo elegido
 * (`docs/referencia-impuestos.md`). La boleta queda como deuda en la cuenta
 * del organismo, lista para conciliar con su pago (tarjeta o banco).
 */
export function ImpuestoForm({ inicial }: { inicial?: ImpuestoDetalle }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { data: catalogo, isLoading, isError, refetch } = useQuery({
    queryKey: ["impuestos-catalogo"],
    queryFn: fetchCatalogoImpuestos,
    staleTime: Infinity,
  });

  const [idOrganismo, setIdOrganismo] = useState<number | null>(inicial?.idOrganismo ?? null);
  const [idTipo, setIdTipo] = useState<number | null>(inicial?.idTipoImpuesto ?? null);
  const [fecha, setFecha] = useState(inicial?.fecha?.slice(0, 10) ?? "");
  const [periodo, setPeriodo] = useState(inicial?.periodoLiquidado ?? "");
  const [numero, setNumero] = useState(inicial?.numeroDocumento ?? "");
  const [importe, setImporte] = useState<number>(inicial?.importe ?? 0);
  const [documento, setDocumento] = useState(inicial?.documentoOriginal ?? "");
  const [error, setError] = useState<string | null>(null);

  const organismo = catalogo?.organismos.find((o) => o.idContacto === idOrganismo);

  const guardar = useMutation({
    mutationFn: (body: ImpuestoInput) =>
      inicial ? editarImpuesto(inicial.idImpuesto, body) : crearImpuesto(body),
    onSuccess: (guardada) => {
      queryClient.invalidateQueries({ queryKey: ["impuestos"] });
      showToast(inicial ? "Boleta actualizada." : `Boleta #${guardada.idImpuesto} cargada.`, "success");
      router.push(`/finanzas/impuestos?highlight=${guardada.idImpuesto}`);
    },
    onError: (err) => setError(mensaje(err)),
  });

  const borrar = useMutation({
    mutationFn: () => eliminarImpuesto(inicial!.idImpuesto),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["impuestos"] });
      showToast("Boleta eliminada.", "success");
      router.push("/finanzas/impuestos");
    },
    onError: (err) => setError(mensaje(err)),
  });

  function enviar(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!idOrganismo || !idTipo || !fecha || !importe) {
      setError("Completá organismo, tipo de impuesto, fecha e importe.");
      return;
    }
    guardar.mutate({
      idOrganismo,
      idTipoImpuesto: idTipo,
      fecha,
      periodoLiquidado: periodo.trim() || null,
      numeroDocumento: numero.trim() || null,
      importe,
      documentoOriginal: documento.trim() || null,
    });
  }

  if (isLoading) return <LoadingState />;
  if (isError || !catalogo) return <ErrorState message="No se pudo cargar el catálogo de impuestos." onRetry={() => refetch()} />;

  return (
    <form onSubmit={enviar} className="max-w-3xl space-y-4 rounded-md border border-border bg-surface p-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <label className={label}>
          Organismo
          <select
            className={input}
            value={idOrganismo ?? ""}
            onChange={(e) => {
              setIdOrganismo(e.target.value ? Number(e.target.value) : null);
              setIdTipo(null);
            }}
          >
            <option value="">Elegí un organismo…</option>
            {catalogo.organismos.map((o) => (
              <option key={o.idContacto} value={o.idContacto}>
                {o.nombre}
              </option>
            ))}
          </select>
        </label>
        <label className={label}>
          Tipo de impuesto
          <select
            className={input}
            value={idTipo ?? ""}
            disabled={!organismo}
            onChange={(e) => setIdTipo(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">{organismo ? "Elegí el impuesto…" : "Primero elegí el organismo"}</option>
            {organismo?.tipos.map((t) => (
              <option key={t.idTipoImpuesto} value={t.idTipoImpuesto}>
                {t.nombre}
              </option>
            ))}
          </select>
        </label>
        <label className={label}>
          Fecha
          <input type="date" className={input} value={fecha} onChange={(e) => setFecha(e.target.value)} />
        </label>
        <label className={label}>
          Período liquidado
          <input className={input} value={periodo} placeholder="Ej. 02 2024 o cuota 1/2024" onChange={(e) => setPeriodo(e.target.value)} />
        </label>
        <label className={label}>
          Nº de documento
          <input className={input} value={numero} placeholder="Nº de boleta, VEP u obligación" onChange={(e) => setNumero(e.target.value)} />
        </label>
        <label className={label}>
          Importe
          <MoneyInput value={importe} onChange={setImporte} moneda="Pesos" className={input} />
        </label>
        <ArchivoVinculado
          className="sm:col-span-2"
          label="Boleta original (opcional)"
          value={documento}
          onChange={setDocumento}
          inputClassName={input}
        />
      </div>

      {error && <p className="text-sm text-status-danger">{error}</p>}

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={guardar.isPending}
          className="rounded bg-finance px-4 py-1.5 text-sm text-white disabled:opacity-60"
        >
          {guardar.isPending ? "Guardando…" : inicial ? "Guardar cambios" : "Cargar boleta"}
        </button>
        {inicial && (
          <button
            type="button"
            disabled={borrar.isPending}
            onClick={() => {
              if (window.confirm("¿Eliminar esta boleta? No se puede deshacer.")) borrar.mutate();
            }}
            className="text-sm text-status-danger underline"
          >
            Eliminar boleta
          </button>
        )}
      </div>
    </form>
  );
}
