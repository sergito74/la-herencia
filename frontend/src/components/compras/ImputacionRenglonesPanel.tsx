"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { useToast } from "@/components/ui/Toast";
import { formatMoneda } from "@/lib/format";
import { apiGet, ApiError, apiPut } from "@/services/apiClient";

interface RenglonTamiz {
  idDetalleCompra: number;
  producto: string | null;
  importe: number;
  destino: string | null;
  idParte: number | null;
  idCultivo: number | null;
  cultivo: string | null;
  idCampania: number | null;
  campania: string | null;
  estado: "Aprobada" | "Pendiente";
  motivo: string | null;
  etiqueta: string;
  sugerido: boolean;
}
interface Catalogo {
  cultivos: { id: number; nombre: string }[];
  campanias: { id: number; nombre: string }[];
}

const DESTINOS: { valor: string; label: string }[] = [
  { valor: "Cultivo", label: "A cultivo" },
  { valor: "CultivoStock", label: "Va a stock" },
  { valor: "Estructura", label: "Gasto general" },
  { valor: "Ganaderia", label: "Ganadería" },
  { valor: "Financiero", label: "Financiero" },
  { valor: "NoImputa", label: "No se imputa" },
];

export const imputacionCompraKey = (idCompra: number) => ["imputacion-tamiz", idCompra];

/** 050 US6 (T041): cómo se imputa cada renglón de la compra. Franja de una línea; el detalle se abre a pedido y
 *  cada renglón se cambia con un clic (opcionalmente, recordándolo para ese producto). */
export function ImputacionRenglonesPanel({ idCompra }: { idCompra: number }) {
  const { data } = useQuery({
    queryKey: imputacionCompraKey(idCompra),
    queryFn: () => apiGet<{ renglones: RenglonTamiz[] }>(`/api/imputacion/tamiz/compra/${idCompra}`),
  });
  const [abierto, setAbierto] = useState(false);
  const cajaRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!abierto) return;
    function fuera(e: MouseEvent) {
      if (cajaRef.current && !cajaRef.current.contains(e.target as Node)) setAbierto(false);
    }
    document.addEventListener("mousedown", fuera);
    return () => document.removeEventListener("mousedown", fuera);
  }, [abierto]);

  const renglones = data?.renglones ?? [];
  if (!renglones.length) return null;
  const revisar = renglones.filter((r) => r.estado !== "Aprobada").length;
  const resumen = [...new Set(renglones.map((r) => r.etiqueta))].join(" · ");

  return (
    <div ref={cajaRef} className="relative">
      <section className="flex h-7 items-center gap-2 rounded border border-border bg-surface px-2 text-xs">
        <span className="shrink-0 font-medium text-ink-secondary">Imputación:</span>
        <div className="flex min-w-0 flex-1 items-center gap-2 overflow-hidden whitespace-nowrap">
          {revisar > 0 ? (
            <span className="font-medium text-status-warning">{revisar} para revisar</span>
          ) : (
            <span className="truncate text-ink-secondary">{resumen}</span>
          )}
        </div>
        <button type="button" onClick={() => setAbierto((a) => !a)} className="shrink-0 text-finance underline">
          {abierto ? "Cerrar" : "Ver renglones"}
        </button>
      </section>
      {abierto && (
        <div className="absolute left-0 right-0 z-20 mt-1 max-h-96 overflow-y-auto rounded border border-border bg-white p-2 shadow-lg">
          <ul className="divide-y text-xs">
            {renglones.map((r) => (
              <RenglonFila key={r.idDetalleCompra} r={r} idCompra={idCompra} />
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function RenglonFila({ r, idCompra }: { r: RenglonTamiz; idCompra: number }) {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const [editando, setEditando] = useState(false);
  const [destino, setDestino] = useState(r.estado === "Aprobada" && r.destino ? r.destino : "Cultivo");
  const [idCultivo, setIdCultivo] = useState<number | "">(r.idCultivo ?? "");
  const [idCampania, setIdCampania] = useState<number | "">(r.idCampania ?? "");
  const [recordar, setRecordar] = useState(false);
  const { data: catalogo } = useQuery({
    queryKey: ["imputacion-tamiz-catalogo"],
    queryFn: () => apiGet<Catalogo>("/api/imputacion/tamiz/catalogo"),
    enabled: editando,
    staleTime: 600_000,
  });

  const guardar = useMutation({
    mutationFn: () =>
      apiPut(`/api/imputacion/tamiz/renglon/${r.idDetalleCompra}`, {
        destino,
        idParte: r.idParte,
        idCultivo: destino === "Cultivo" ? idCultivo || null : null,
        idCampania: destino === "Cultivo" ? idCampania || null : null,
        guardarRegla: recordar,
      }),
    onSuccess: () => {
      showToast(recordar ? "Guardado. Este producto se va a imputar así de ahora en adelante." : "Imputación guardada.", "success");
      setEditando(false);
      qc.invalidateQueries({ queryKey: imputacionCompraKey(idCompra) });
      qc.invalidateQueries({ queryKey: ["imputacion-revisar"] });
      qc.invalidateQueries({ queryKey: ["resultado-cultivo"] });
    },
    onError: (e) => showToast(e instanceof ApiError ? e.message : "No se pudo guardar la imputación.", "danger"),
  });

  const destinoTexto = [r.etiqueta, r.cultivo, r.campania].filter(Boolean).join(" · ");
  return (
    <li className="space-y-1 py-1.5">
      <div className="flex items-center gap-2">
        <span className="min-w-0 flex-1 truncate">{r.producto}</span>
        <span className="shrink-0 tabular-nums text-ink-secondary">{formatMoneda(r.importe)}</span>
        <span
          className={`shrink-0 rounded-full px-2 py-0.5 ${
            r.estado === "Aprobada" ? "bg-surface-sunken text-ink-primary" : "bg-status-warning-bg text-status-warning"
          }`}
        >
          {destinoTexto}
          {r.sugerido && r.estado === "Aprobada" && <span className="ml-1 text-ink-muted">(sugerido)</span>}
        </span>
        <SoloLectura>
          <button type="button" onClick={() => setEditando((e) => !e)} className="shrink-0 text-finance underline">
            {editando ? "Cancelar" : "Cambiar"}
          </button>
        </SoloLectura>
      </div>
      {r.estado !== "Aprobada" && r.motivo && <p className="text-status-warning">{r.motivo}</p>}
      {editando && (
        <div className="flex flex-wrap items-center gap-2 rounded bg-surface-sunken p-2">
          <select value={destino} onChange={(e) => setDestino(e.target.value)} className="rounded border px-1 py-0.5">
            {DESTINOS.map((d) => (
              <option key={d.valor} value={d.valor}>{d.label}</option>
            ))}
          </select>
          {destino === "Cultivo" && (
            <>
              <select value={idCultivo} onChange={(e) => setIdCultivo(e.target.value ? Number(e.target.value) : "")} className="rounded border px-1 py-0.5">
                <option value="">Cultivo…</option>
                {catalogo?.cultivos.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
              </select>
              <select value={idCampania} onChange={(e) => setIdCampania(e.target.value ? Number(e.target.value) : "")} className="rounded border px-1 py-0.5">
                <option value="">Campaña…</option>
                {catalogo?.campanias.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
              </select>
            </>
          )}
          <label className="flex items-center gap-1">
            <input type="checkbox" checked={recordar} onChange={(e) => setRecordar(e.target.checked)} />
            Recordar para este producto
          </label>
          <button
            type="button"
            disabled={guardar.isPending || (destino === "Cultivo" && (!idCultivo || !idCampania))}
            onClick={() => guardar.mutate()}
            className="rounded bg-agro px-2 py-0.5 text-white disabled:opacity-60"
          >
            Guardar
          </button>
        </div>
      )}
    </li>
  );
}
