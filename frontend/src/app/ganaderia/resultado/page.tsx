"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { CuadroResultado } from "@/components/ganaderia/CuadroResultado";
import { PageHeader } from "@/components/ui/PageHeader";
import { Segmentos } from "@/components/ui/Segmentos";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import {
  fetchResultadoGanadero,
  recalcularResultadoGanadero,
  type MonedaGanaderia,
  type VistaGanaderia,
} from "@/services/ganaderiaApi";

function anioActual(vista: VistaGanaderia): number {
  const hoy = new Date();
  const mes = hoy.getMonth() + 1;
  return mes >= (vista === "ejercicio" ? 4 : 7) ? hoy.getFullYear() : hoy.getFullYear() - 1;
}

const etiqueta = (a: number) => `${a}/${String(a + 1).slice(-2)}`;

/** 052 US1: resultado ganadero por ejercicio (o campaña jul–jun para comparar con la planilla histórica). */
export default function ResultadoGanaderoPage() {
  const [vista, setVista] = useState<VistaGanaderia>("ejercicio");
  const [moneda, setMoneda] = useState<MonedaGanaderia>("USD");
  const [cantidad, setCantidad] = useState<"5" | "10">("5");
  const [campo, setCampo] = useState<"todos" | "1" | "2">("todos");
  const establecimiento = campo === "todos" ? undefined : Number(campo);
  const hasta = anioActual(vista);
  const desde = hasta - Number(cantidad) + 1;
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["ganaderia", "resultado", vista, moneda, desde, hasta, campo],
    queryFn: () => fetchResultadoGanadero(vista, moneda, etiqueta(desde), etiqueta(hasta), establecimiento),
    staleTime: 5 * 60_000,
  });
  const recalcular = useMutation({
    mutationFn: recalcularResultadoGanadero,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ganaderia", "resultado"] }),
  });

  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Resultado ganadero"
        ayuda="Ventas de hacienda, pastaje y costos imputados a la ganadería (sanidad, alimentación, forrajes y silo, personal), con el margen bruto, la estructura y el resultado operativo. Hacé clic en un importe para ver los comprobantes.">
        <button type="button" onClick={() => recalcular.mutate()} disabled={recalcular.isPending}
          className="rounded-md border border-border px-2.5 py-1 text-sm hover:bg-surface-sunken disabled:opacity-50">
          {recalcular.isPending ? "Recalculando…" : "Recalcular"}
        </button>
      </PageHeader>
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <Segmentos size="sm" etiqueta="Período" valor={vista} onChange={setVista}
          opciones={[{ id: "ejercicio", label: "Ejercicio (abr–mar)" }, { id: "campania", label: "Campaña (jul–jun)" }]} />
        <Segmentos size="sm" etiqueta="Moneda" valor={moneda} onChange={setMoneda}
          opciones={[{ id: "USD", label: "us$" }, { id: "ARS", label: "$" }]} />
        <Segmentos size="sm" etiqueta="Cantidad de períodos" valor={cantidad} onChange={setCantidad}
          opciones={[{ id: "5", label: "Últimos 5" }, { id: "10", label: "Últimos 10" }]} />
        <Segmentos size="sm" etiqueta="Campo" valor={campo} onChange={setCampo}
          opciones={[{ id: "todos", label: "Todos los campos" }, { id: "1", label: "La Herencia" }, { id: "2", label: "San Pedro" }]} />
        {q.data?.conversion && <span className="text-xs text-ink-muted">Dólar: {q.data.conversion}</span>}
      </div>
      {vista === "campania" && (
        <p className="mb-2 text-sm text-ink-secondary">
          Por campaña el resultado es un margen de caja: no incluye la variación del stock de hacienda.
        </p>
      )}
      {q.isLoading ? <LoadingState rows={12} />
        : q.isError ? <ErrorState message="No se pudo calcular el resultado ganadero." onRetry={() => q.refetch()} />
        : !q.data || !q.data.filas.length ? <EmptyState message="No hay ventas ni costos ganaderos en estos períodos." />
        : (
          <>
            {q.data.nota && <p className="mb-2 text-sm text-ink-secondary">{q.data.nota}</p>}
            <CuadroResultado datos={q.data} vista={vista} establecimiento={establecimiento} />
            {q.data.avisos.length > 0 && (
              <p className="mt-2 text-xs text-ink-muted">
                Todavía no hay stock de hacienda valuado: el ingreso neto no incluye la diferencia de inventario. Se completa
                cuando se cargue el stock.
              </p>
            )}
          </>
        )}
    </main>
  );
}
