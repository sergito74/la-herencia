"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";

import { formatFecha } from "@/lib/format";
import { apiGet, apiPost } from "@/services/apiClient";

interface Problema {
  tipo: string;
  idCompra: number | null;
  documento: string;
  detalle: string;
}
interface Estado {
  fecha: string | null;
  controlando: boolean;
  problemas: Problema[];
  error: string | null;
}

/** 050: control de integridad de los costos. Corre solo una vez por día; si algo no cierra, se lista por documento. */
export function ControlCostos() {
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ["imputacion-control"],
    queryFn: () => apiGet<Estado>("/api/imputacion/control"),
    refetchInterval: (q) => (q.state.data?.controlando ? 10_000 : 5 * 60_000),
  });
  const controlar = useMutation({
    mutationFn: () => apiPost<Estado>("/api/imputacion/control/controlar", {}),
    onSuccess: (d) => qc.setQueryData(["imputacion-control"], d),
  });
  if (!data) return null;
  const hora = data.fecha ? `${formatFecha(data.fecha)} ${data.fecha.slice(11, 16)}` : null;
  const boton = (
    <button type="button" disabled={data.controlando || controlar.isPending} onClick={() => controlar.mutate()} className="underline disabled:opacity-60">
      {data.controlando ? "Controlando…" : "Controlar ahora"}
    </button>
  );

  if (!data.problemas.length) {
    return (
      <p className="mt-3 flex flex-wrap items-center gap-2 text-xs text-ink-secondary">
        <span>
          Control de costos{hora ? ` del ${hora}` : ""}: {data.fecha ? "todo cierra." : "en curso…"}
        </span>
        {data.fecha && boton}
      </p>
    );
  }
  return (
    <section className="mt-3 space-y-2 rounded border border-status-danger bg-status-danger-bg p-3">
      <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
        <h2 className="font-semibold text-status-danger">
          Control de costos{hora ? ` del ${hora}` : ""}: {data.problemas.length} diferencia{data.problemas.length === 1 ? "" : "s"}
        </h2>
        <span className="text-xs">{boton}</span>
      </div>
      <p className="text-xs text-ink-secondary">Mientras esto no se resuelva, el costo de algún cultivo puede estar mal calculado.</p>
      <ul className="divide-y rounded border bg-white text-sm">
        {data.problemas.map((p, i) => (
          <li key={i} className="space-y-0.5 p-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span>
                <strong>{p.tipo}</strong>
                {p.documento && <> · {p.documento}</>}
              </span>
              {p.idCompra && (
                <Link className="text-finance underline" href={`/compras/${p.idCompra}/editar`}>
                  Abrir la compra
                </Link>
              )}
            </div>
            <p className="text-xs text-ink-secondary">{p.detalle}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
