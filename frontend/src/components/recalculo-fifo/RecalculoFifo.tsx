"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { SideDrawer } from "@/components/ui/SideDrawer";
import { StatusBadge, type BadgeTone } from "@/components/ui/StatusBadge";
import { useToast } from "@/components/ui/Toast";
import { formatFecha, formatMoneda } from "@/lib/format";
import { ApiError } from "@/services/apiClient";
import {
  aplicarEjecucion,
  descartarEjecucion,
  revertirEjecucion,
  fetchContactos,
  fetchDetalleContacto,
  fetchEjecuciones,
  marcarExcepcion,
  simular,
  type Alcance,
  type ContactoEjecucion,
  type Ejecucion,
  type FiltroContactos,
  type Tendencia,
} from "@/services/recalculoFifoApi";

const FILTROS: { valor: FiltroContactos; texto: string }[] = [
  { valor: "todos", texto: "Todos" },
  { valor: "excepcion", texto: "Excepciones pendientes" },
  { valor: "no-cierra", texto: "No cierran" },
  { valor: "cierra", texto: "Cierran" },
  { valor: "mejora", texto: "Mejoran" },
  { valor: "empeora", texto: "Empeoran" },
];

const TENDENCIA: Record<Tendencia, { texto: string; tono: BadgeTone }> = {
  igual: { texto: "Igual", tono: "neutral" },
  mejora: { texto: "Mejora", tono: "success" },
  empeora: { texto: "Empeora", tono: "danger" },
};

const REGLA: Record<string, string> = {
  cadena: "Cadena tarjeta/cheque",
  eleccion: "Elección manual",
  "nota-origen": "NC a su factura",
  "ajuste-tc": "Ajuste de tipo de cambio",
  compensacion: "Compensación",
  fifo: "FIFO",
  anticipo: "Anticipo",
  reintegro: "Reintegro",
};

const PAGINA = 50;

function mensaje(e: unknown): string {
  return e instanceof ApiError ? e.message : "No se pudo completar la operación.";
}

function pesos(v: number): string {
  return formatMoneda(v, "Pesos");
}

function moneda(v: number, m: "ARS" | "USD"): string {
  return formatMoneda(v, m === "USD" ? "Dolares" : "Pesos");
}

function Cierre({ valor }: { valor: boolean }) {
  return <StatusBadge label={valor ? "Cierra" : "No cierra"} tone={valor ? "success" : "warning"} />;
}

function BarraEjecucion({
  ejecuciones,
  actual,
  onElegir,
}: {
  ejecuciones: Ejecucion[];
  actual: Ejecucion | undefined;
  onElegir: (id: number) => void;
}) {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const accion = useMutation({
    mutationFn: async (fn: () => Promise<unknown>) => fn(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["recalculo-fifo"] }),
    onError: (e) => showToast(mensaje(e), "danger"),
  });
  const lanzar = (alcance: Alcance) =>
    accion.mutate(async () => {
      const r = await simular(alcance);
      onElegir(r.idEjecucion);
      showToast(`Simulación ${r.idEjecucion} lista: ${r.resumen.contactos} contactos.`, "success");
    });
  const r = actual?.resumen;
  return (
    <div className="space-y-3 rounded-md border border-border bg-surface p-4">
      <div className="flex flex-wrap items-center gap-3">
        <label className="text-sm text-ink-secondary" htmlFor="ejecucion">
          Simulación
        </label>
        <select
          id="ejecucion"
          className="rounded-md border border-border bg-surface px-2 py-1 text-sm"
          value={actual?.idEjecucion ?? ""}
          onChange={(e) => onElegir(Number(e.target.value))}
        >
          {ejecuciones.map((e) => (
            <option key={e.idEjecucion} value={e.idEjecucion}>
              N.º {e.idEjecucion} · {formatFecha(e.fechaInicio)} · {e.estado} ·{" "}
              {Array.isArray(e.alcance) ? `${e.alcance.length} contactos` : e.alcance}
            </option>
          ))}
        </select>
        <SoloLectura>
          <button
            type="button"
            className="rounded-md bg-finance px-3 py-1.5 text-sm text-white disabled:opacity-50"
            disabled={accion.isPending}
            onClick={() => lanzar("etapa-1")}
          >
            {accion.isPending ? "Simulando…" : "Simular primera etapa (9 contactos)"}
          </button>
          <button
            type="button"
            className="rounded-md border border-border px-3 py-1.5 text-sm disabled:opacity-50"
            disabled={accion.isPending}
            onClick={() => lanzar("todos")}
          >
            Simular todos los contactos
          </button>
          {actual?.estado === "simulada" && (
            <button
              type="button"
              className="rounded-md bg-status-success px-3 py-1.5 text-sm text-white disabled:opacity-50"
              disabled={accion.isPending}
              onClick={() => {
                const n = actual.resumen?.cierranDespues ?? 0;
                if (
                  !window.confirm(
                    `Se aplicará el recálculo a los ${n} contactos que cierran. Antes se toma un respaldo verificado y ` +
                      "la operación se puede revertir. ¿Continuar?"
                  )
                )
                  return;
                accion.mutate(async () => {
                  const r = await aplicarEjecucion(actual.idEjecucion, null);
                  showToast(
                    `Aplicado a ${r.aplicados.length} contactos (${r.sinCambios.length} sin cambios).`,
                    "success"
                  );
                });
              }}
            >
              Aplicar a los contactos que cierran
            </button>
          )}
          {actual?.estado === "aplicada" && (
            <button
              type="button"
              className="rounded-md border border-status-danger px-3 py-1.5 text-sm text-status-danger disabled:opacity-50"
              disabled={accion.isPending}
              onClick={() => {
                if (!window.confirm("Se restaurarán las aplicaciones anteriores a esta ejecución. ¿Continuar?")) return;
                accion.mutate(() => revertirEjecucion(actual.idEjecucion));
              }}
            >
              Revertir esta aplicación
            </button>
          )}
          {actual?.estado === "simulada" && (
            <button
              type="button"
              className="rounded-md border border-border px-3 py-1.5 text-sm text-ink-secondary disabled:opacity-50"
              disabled={accion.isPending}
              onClick={() => accion.mutate(() => descartarEjecucion(actual.idEjecucion))}
            >
              Descartar esta simulación
            </button>
          )}
        </SoloLectura>
      </div>
      {r && (
        <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-6">
          <div>
            <dt className="text-ink-secondary">Contactos</dt>
            <dd className="text-lg font-semibold">{r.contactos}</dd>
          </div>
          <div>
            <dt className="text-ink-secondary">Cerraban antes</dt>
            <dd className="text-lg font-semibold">{r.cerrabanAntes}</dd>
          </div>
          <div>
            <dt className="text-ink-secondary">Cierran después</dt>
            <dd className="text-lg font-semibold">{r.cierranDespues}</dd>
          </div>
          <div>
            <dt className="text-ink-secondary">Mejoran</dt>
            <dd className="text-lg font-semibold">{r.mejoran}</dd>
          </div>
          <div>
            <dt className="text-ink-secondary">Empeoran</dt>
            <dd className="text-lg font-semibold">{r.empeoran}</dd>
          </div>
          <div>
            <dt className="text-ink-secondary">Excepciones</dt>
            <dd className="text-lg font-semibold">{r.excepciones}</dd>
          </div>
        </dl>
      )}
      <p className="text-xs text-ink-secondary">
        La simulación no modifica las aplicaciones reales. Solo guarda el resultado propuesto para revisarlo.
      </p>
    </div>
  );
}

function DetallePanel({ idEjecucion, contacto }: { idEjecucion: number; contacto: ContactoEjecucion }) {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const [nota, setNota] = useState(contacto.notaExcepcion ?? "");
  const detalle = useQuery({
    queryKey: ["recalculo-fifo", "detalle", idEjecucion, contacto.idContacto],
    queryFn: () => fetchDetalleContacto(idEjecucion, contacto.idContacto),
  });
  const excepcion = useMutation({
    mutationFn: (estado: "pendiente" | "resuelta") =>
      marcarExcepcion(idEjecucion, contacto.idContacto, estado, nota || null),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["recalculo-fifo"] });
      showToast("Excepción actualizada.", "success");
    },
    onError: (e) => showToast(mensaje(e), "danger"),
  });
  if (detalle.isLoading) return <LoadingState />;
  if (detalle.isError || !detalle.data)
    return <ErrorState message="No se pudo leer el detalle." onRetry={() => detalle.refetch()} />;
  const d = detalle.data;
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm text-ink-secondary">Antes</span>
        <Cierre valor={contacto.cerrabaAntes} />
        <span className="text-sm text-ink-secondary">Después</span>
        <Cierre valor={contacto.cierraDespues} />
        <StatusBadge label={TENDENCIA[contacto.tendencia].texto} tone={TENDENCIA[contacto.tendencia].tono} />
      </div>
      {(contacto.controles.length > 0 || contacto.marcas.length > 0) && (
        <ul className="space-y-1 text-sm">
          {contacto.controles.map((c) => (
            <li key={c.codigo} className="text-status-danger">
              • {c.descripcion}
            </li>
          ))}
          {contacto.marcas.map((m, i) => (
            <li key={`${m.codigo}-${i}`} className="text-ink-secondary">
              • {m.descripcion}
            </li>
          ))}
        </ul>
      )}
      {!contacto.cierraDespues && (
        <SoloLectura>
          <div className="flex flex-wrap items-end gap-2">
            <label className="flex-1 text-sm">
              <span className="text-ink-secondary">Nota de revisión</span>
              <input
                className="mt-1 w-full rounded-md border border-border bg-surface px-2 py-1"
                value={nota}
                onChange={(e) => setNota(e.target.value)}
              />
            </label>
            <button
              type="button"
              className="rounded-md border border-border px-3 py-1.5 text-sm"
              onClick={() => excepcion.mutate(contacto.estadoExcepcion === "resuelta" ? "pendiente" : "resuelta")}
            >
              {contacto.estadoExcepcion === "resuelta" ? "Volver a pendiente" : "Marcar como revisada"}
            </button>
          </div>
        </SoloLectura>
      )}
      <section>
        <h3 className="mb-2 font-semibold">Cuenta, renglón por renglón</h3>
        <div className="max-h-[45vh] overflow-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-surface text-left text-ink-secondary">
              <tr>
                <th className="py-1 pr-2">Fecha</th>
                <th className="pr-2">Vence</th>
                <th className="pr-2">Comprobante</th>
                <th className="pr-2 text-right">Debe</th>
                <th className="pr-2 text-right">Haber</th>
                <th className="pr-2 text-right">Aplicado</th>
                <th className="text-right">Saldo $</th>
              </tr>
            </thead>
            <tbody>
              {d.renglones.map((r) => (
                <tr key={`${r.origen}-${r.id}-${r.cuota ?? 0}`} className="border-t border-border">
                  <td className="py-1 pr-2">{formatFecha(r.fecha)}</td>
                  <td className="pr-2">{r.clase === "doc" ? formatFecha(r.vencimiento) : ""}</td>
                  <td className="pr-2">
                    {r.documento ?? r.origen} {r.nro}
                    {r.cuota ? ` (cuota ${r.cuota})` : ""}
                    {r.suspendido ? " · suspendida" : ""}
                  </td>
                  <td className="pr-2 text-right">{r.lado === "D" ? moneda(r.importe, r.moneda) : ""}</td>
                  <td className="pr-2 text-right">{r.lado === "C" ? moneda(r.importe, r.moneda) : ""}</td>
                  <td className={`pr-2 text-right ${Math.abs(r.aplicado - r.importe) > 0.01 ? "text-status-warning" : ""}`}>
                    {moneda(r.aplicado, r.moneda)}
                  </td>
                  <td className="text-right">{pesos(r.saldoAcumuladoArs)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section>
        <h3 className="mb-2 font-semibold">Vínculos propuestos ({d.aplicaciones.length})</h3>
        <div className="max-h-[35vh] overflow-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-surface text-left text-ink-secondary">
              <tr>
                <th className="py-1 pr-2">Regla</th>
                <th className="pr-2">Pago / cobro</th>
                <th className="pr-2">Documento</th>
                <th className="pr-2 text-right">Importe</th>
                <th className="pr-2 text-right">TC</th>
                <th className="text-right">Dif. cambio $</th>
              </tr>
            </thead>
            <tbody>
              {d.aplicaciones.map((a, i) => (
                <tr key={i} className="border-t border-border">
                  <td className="py-1 pr-2">{REGLA[a.regla] ?? a.regla}</td>
                  <td className="pr-2">
                    {a.credito.origen} {a.credito.id} · {formatFecha(a.fechaCredito)}
                  </td>
                  <td className="pr-2">
                    {a.debito.origen} {a.debito.id}
                    {a.debito.cuota ? ` c${a.debito.cuota}` : ""} · vence {formatFecha(a.fechaVencimiento)}
                  </td>
                  <td className="pr-2 text-right">{moneda(a.importeAplicado, a.moneda)}</td>
                  <td className="pr-2 text-right">{a.tipoCambio ? formatMoneda(a.tipoCambio, "Pesos") : ""}</td>
                  <td className="text-right">{a.diferenciaCambio ? pesos(a.diferenciaCambio) : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

export function RecalculoFifo() {
  const [elegida, setElegida] = useState<number | null>(null);
  const [filtro, setFiltro] = useState<FiltroContactos>("todos");
  const [pagina, setPagina] = useState(1);
  const [abierto, setAbierto] = useState<ContactoEjecucion | null>(null);
  const ejecuciones = useQuery({ queryKey: ["recalculo-fifo", "ejecuciones"], queryFn: fetchEjecuciones });
  const actual = ejecuciones.data?.find((e) => e.idEjecucion === elegida) ?? ejecuciones.data?.[0];
  const contactos = useQuery({
    queryKey: ["recalculo-fifo", "contactos", actual?.idEjecucion, filtro, pagina],
    queryFn: () => fetchContactos(actual!.idEjecucion, filtro, pagina, PAGINA),
    enabled: actual !== undefined,
  });

  if (ejecuciones.isLoading) return <LoadingState />;
  if (ejecuciones.isError)
    return <ErrorState message="No se pudieron leer las simulaciones." onRetry={() => ejecuciones.refetch()} />;

  return (
    <div className="space-y-4">
      <BarraEjecucion
        ejecuciones={ejecuciones.data ?? []}
        actual={actual}
        onElegir={(id) => {
          setElegida(id);
          setPagina(1);
        }}
      />
      {!actual ? (
        <EmptyState message="Todavía no hay simulaciones. Empezá por la primera etapa." />
      ) : (
        <>
          <div className="flex flex-wrap gap-2">
            {FILTROS.map((f) => (
              <button
                key={f.valor}
                type="button"
                className={`rounded-full border px-3 py-1 text-sm ${
                  filtro === f.valor ? "border-finance bg-finance text-white" : "border-border"
                }`}
                onClick={() => {
                  setFiltro(f.valor);
                  setPagina(1);
                }}
              >
                {f.texto}
              </button>
            ))}
          </div>
          {contactos.isLoading ? (
            <LoadingState />
          ) : contactos.isError || !contactos.data ? (
            <ErrorState message="No se pudieron leer los contactos." onRetry={() => contactos.refetch()} />
          ) : contactos.data.items.length === 0 ? (
            <EmptyState message="No hay contactos con este filtro." />
          ) : (
            <>
              <table className="w-full text-sm">
                <thead className="text-left text-ink-secondary">
                  <tr>
                    <th className="py-2 pr-2">Contacto</th>
                    <th className="pr-2 text-right">Facturado $</th>
                    <th className="pr-2 text-right">Pagado / cobrado $</th>
                    <th className="pr-2 text-right">Aplicado antes $</th>
                    <th className="pr-2 text-right">Aplicado después $</th>
                    <th className="pr-2 text-right">Dinero sin aplicar $</th>
                    <th className="pr-2">Antes</th>
                    <th className="pr-2">Después</th>
                    <th className="pr-2">Tendencia</th>
                    <th>Motivo</th>
                  </tr>
                </thead>
                <tbody>
                  {contactos.data.items.map((c) => (
                    <tr
                      key={c.idContacto}
                      className="cursor-pointer border-t border-border hover:bg-surface-sunken"
                      onClick={() => setAbierto(c)}
                    >
                      <td className="py-2 pr-2">
                        {c.nombre}
                        {c.moneda === "USD" && <span className="ml-1 text-xs text-ink-secondary">(us$)</span>}
                      </td>
                      <td className="pr-2 text-right">{pesos(c.facturadoAntes)}</td>
                      <td className="pr-2 text-right">{pesos(c.pagadoAntes)}</td>
                      <td className="pr-2 text-right">{pesos(c.aplicadoAntes)}</td>
                      <td className="pr-2 text-right">{pesos(c.aplicadoDespues)}</td>
                      <td className="pr-2 text-right">{c.anticipoAbierto ? pesos(c.anticipoAbierto) : ""}</td>
                      <td className="pr-2">
                        <Cierre valor={c.cerrabaAntes} />
                      </td>
                      <td className="pr-2">
                        <Cierre valor={c.cierraDespues} />
                      </td>
                      <td className="pr-2">
                        <StatusBadge label={TENDENCIA[c.tendencia].texto} tone={TENDENCIA[c.tendencia].tono} />
                      </td>
                      <td className="text-xs text-ink-secondary">
                        {c.controles.map((x) => x.descripcion).join(" ")}
                        {c.estadoExcepcion === "resuelta" ? " (revisada)" : ""}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {contactos.data.total > PAGINA && (
                <div className="flex items-center gap-3 text-sm">
                  <button type="button" disabled={pagina === 1} onClick={() => setPagina((p) => p - 1)}>
                    ← Anterior
                  </button>
                  <span>
                    Página {pagina} de {Math.ceil(contactos.data.total / PAGINA)}
                  </span>
                  <button
                    type="button"
                    disabled={pagina * PAGINA >= contactos.data.total}
                    onClick={() => setPagina((p) => p + 1)}
                  >
                    Siguiente →
                  </button>
                </div>
              )}
            </>
          )}
        </>
      )}
      <SideDrawer open={abierto !== null} onClose={() => setAbierto(null)} title={abierto?.nombre ?? ""} maxWidthClass="max-w-6xl">
        {abierto && actual && <DetallePanel idEjecucion={actual.idEjecucion} contacto={abierto} />}
      </SideDrawer>
    </div>
  );
}
