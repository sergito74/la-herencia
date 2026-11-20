"use client";

import { Flotante } from "@/components/ui/Flotante";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { ChipDestino, ChipsDestino } from "@/components/imputacion/ChipsDestino";
import { ControlDrawer, useControlCostos } from "@/components/imputacion/ControlDrawer";
import { DocumentoDrawer } from "@/components/imputacion/DocumentoDrawer";
import { TONO_ESTADO } from "@/components/imputacion/estadoDocumento";
import { Button } from "@/components/ui/Button";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { PageHeader } from "@/components/ui/PageHeader";
import { RangoFechas, type Rango } from "@/components/ui/RangoFechas";
import { Segmentos } from "@/components/ui/Segmentos";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { TiraIndicadores } from "@/components/ui/TiraIndicadores";
import { useToast } from "@/components/ui/Toast";
import { formatCantidad, formatFecha, formatMoneda } from "@/lib/format";
import { API_BASE_URL, ApiError, apiPost } from "@/services/apiClient";
import { aprobarCorridas, fetchResumenDocumentos, type DocumentoFila, type EstadoDoc } from "@/services/imputacionDocumentosApi";

const TAM = 50;
const ABREV: Record<string, string> = { Factura: "FC", "Nota de Credito": "NC", "Nota de Crédito": "NC", "Nota de Debito": "ND", "Nota de Débito": "ND" };
type Agrupar = "documento" | "destino" | "proveedor";

function MasAcciones({ exportar }: { exportar: string }) {
  const [abierto, setAbierto] = useState(false);
  const { showToast } = useToast();
  const qc = useQueryClient();
  const caja = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!abierto) return;
    const fuera = (e: MouseEvent) => { if (caja.current && !caja.current.contains(e.target as Node)) setAbierto(false); };
    document.addEventListener("mousedown", fuera);
    return () => document.removeEventListener("mousedown", fuera);
  }, [abierto]);
  const correr = async (fn: () => Promise<string>) => {
    setAbierto(false);
    try { showToast(await fn(), "success"); qc.invalidateQueries({ queryKey: ["imputacion-docs"] }); }
    catch (e) { showToast(e instanceof ApiError ? e.message : "No se pudo completar.", "danger"); }
  };
  return (
    <div className="relative" ref={caja}>
      <Button onClick={() => setAbierto((v) => !v)} aria-haspopup="menu" aria-expanded={abierto}>Más acciones ▾</Button>
      <Flotante ancla={caja} abierto={!!(abierto)} alinear="derecha" className="w-72 rounded-lg border border-border bg-surface p-1 text-sm shadow-lg">
<div role="menu" >
          <a role="menuitem" href={exportar} className="block rounded-md px-3 py-2 hover:bg-surface-sunken">Exportar a Excel (con estos filtros)</a>
          <SoloLectura>
            <button role="menuitem" type="button" className="block w-full rounded-md px-3 py-2 text-left hover:bg-surface-sunken"
              onClick={() => correr(async () => { const r = await apiPost<{ insumosCalculados: number; contratistasCalculados: number }>("/api/imputacion/calcular-pendientes", {});
                return `Calculado: ${r.insumosCalculados} renglones de insumos y ${r.contratistasCalculados} de contratistas.`; })}>Calcular lo pendiente ahora</button>
            <button role="menuitem" type="button" className="block w-full rounded-md px-3 py-2 text-left hover:bg-surface-sunken"
              onClick={() => correr(async () => { const r = await apiPost<{ filas: number }>("/api/imputacion/listado-estudio/generar", {});
                return `Listado para el Estudio actualizado (${formatCantidad(r.filas)} filas).`; })}>Actualizar el listado para el Estudio</button>
          </SoloLectura>
        </div>
</Flotante>
    </div>
  );
}

function Pagina() {
  const params = useSearchParams();
  const qc = useQueryClient();
  const { showToast } = useToast();
  const [rango, setRango] = useState<Rango>({ desde: "", hasta: "" });
  const [idContacto, setIdContacto] = useState<number | null>(null);
  const [proveedor, setProveedor] = useState<string | null>(null);
  const [estado, setEstado] = useState<EstadoDoc | "">((params.get("estado") as EstadoDoc) || "");
  const [destino, setDestino] = useState(params.get("destino") ?? "");
  const [agrupar, setAgrupar] = useState<Agrupar>("documento");
  const [page, setPage] = useState(1);
  const [abierto, setAbierto] = useState<DocumentoFila | null>(null);
  const [control, setControl] = useState(false);
  const [elegidos, setElegidos] = useState<Set<number>>(new Set());
  useEffect(() => { setPage(1); setElegidos(new Set()); }, [rango, idContacto, estado, destino]);

  const filtros = { idContacto, fechaDesde: rango.desde, fechaHasta: rango.hasta, estado, destino, page, pageSize: TAM };
  const q = useQuery({ queryKey: ["imputacion-docs", filtros], queryFn: () => fetchResumenDocumentos(filtros), placeholderData: (p) => p });
  const ctrl = useControlCostos();
  const aprobar = useMutation({
    mutationFn: (ids: string[]) => aprobarCorridas(ids),
    onSuccess: (r) => { showToast(`Aprobados: ${r.aprobadas}${r.fallidas ? ` · ${r.fallidas} cambiaron y hay que revisarlos` : ""}.`, r.fallidas ? "neutral" : "success");
      setElegidos(new Set()); qc.invalidateQueries({ queryKey: ["imputacion-docs"] }); },
    onError: () => showToast("No se pudo aprobar.", "danger"),
  });

  const d = q.data;
  const cuenta = (k: EstadoDoc) => d?.porEstado.find((x) => x.clave === k);
  const avisos = ctrl.data?.problemas.length ?? 0;
  const exportar = (() => {
    const u = new URL("/api/imputacion/documentos/exportar", API_BASE_URL);
    if (idContacto) u.searchParams.set("idContacto", String(idContacto));
    if (rango.desde) u.searchParams.set("fechaDesde", rango.desde);
    if (rango.hasta) u.searchParams.set("fechaHasta", rango.hasta);
    return u.toString();
  })();
  const seleccionables = (d?.items ?? []).filter((r) => r.corridasPendientes.length);
  const corridasElegidas = (d?.items ?? []).filter((r) => elegidos.has(r.idCompra)).flatMap((r) => r.corridasPendientes);

  const columnas: DataTableColumn<DocumentoFila>[] = [
    ...(seleccionables.length ? [{
      key: "sel", header: "", width: "2.25rem",
      render: (r: DocumentoFila) => r.corridasPendientes.length ? (
        <input type="checkbox" aria-label="Elegir para aprobar" checked={elegidos.has(r.idCompra)}
          onChange={(e) => setElegidos((s) => { const n = new Set(s); if (e.target.checked) n.add(r.idCompra); else n.delete(r.idCompra); return n; })} />) : null,
    }] : []),
    { key: "fecha", header: "Fecha", width: "6.5rem", render: (r) => formatFecha(r.fecha) },
    { key: "proveedor", header: "Proveedor", width: "16rem", render: (r) => <span className="block truncate" title={r.proveedor ?? ""}>{r.proveedor ?? "—"}</span> },
    { key: "doc", header: "Documento", width: "11rem", render: (r) => <span className="font-data text-ink-secondary">{ABREV[r.tipoDocumento ?? ""] ?? r.tipoDocumento} {r.numeroDocumento}</span> },
    { key: "destinos", header: "A dónde fue", wrap: true, render: (r) => <ChipsDestino destinos={r.destinos} /> },
    { key: "importe", header: "Importe", align: "right", numeric: true, width: "9.5rem", render: (r) => formatMoneda(r.importe) },
    { key: "estado", header: "Estado", width: "10rem", render: (r) => <StatusBadge label={r.estadoTexto} tone={TONO_ESTADO[r.estado]} /> },
  ];

  return (
    <main className="mx-auto max-w-none space-y-2 px-6 py-3">
      <PageHeader titulo="Imputación de compras" ayuda="A dónde fue cada compra: Adm. General u otro centro de costos, ganadería, un cultivo y campaña, o el stock. Hacé clic en una fila para ver el detalle. El costo de los cultivos está en Producción › Costo por cultivo.">
        <div className="ml-auto"><MasAcciones exportar={exportar} /></div>
      </PageHeader>

      <TiraIndicadores items={[
        { titulo: "Imputado", valor: d ? formatMoneda(d.importe) : "…", pie: d ? `${formatCantidad(d.total)} documentos` : undefined },
        { titulo: "Para revisar", valor: formatCantidad((cuenta("revisar")?.cantidad ?? 0) + (cuenta("decision")?.cantidad ?? 0)),
          aviso: !!((cuenta("revisar")?.cantidad ?? 0) + (cuenta("decision")?.cantidad ?? 0)), activo: estado === "revisar",
          onClick: () => setEstado(estado === "revisar" ? "" : "revisar") },
        { titulo: "Pendientes de aprobar", valor: formatCantidad(cuenta("pendiente")?.cantidad ?? 0),
          pie: cuenta("pendiente")?.importe ? formatMoneda(cuenta("pendiente")!.importe) : undefined, activo: estado === "pendiente",
          onClick: () => setEstado(estado === "pendiente" ? "" : "pendiente") },
        { titulo: "Control de costos", valor: ctrl.data ? (avisos ? `${avisos} aviso${avisos === 1 ? "" : "s"}` : "Todo cierra") : "…",
          aviso: avisos > 0, onClick: () => setControl(true) },
      ]} />

      <section className="space-y-2 rounded-lg border border-border bg-surface px-3 py-2">
        <div className="flex flex-wrap items-center gap-2">
          <RangoFechas valor={rango} onChange={setRango} etiqueta="" />
          <div className="w-56">
            <ContactoSelect value={idContacto} razonSocial={proveedor} onChange={(id, n) => { setIdContacto(id); setProveedor(n); }} placeholder="Proveedor…" ariaLabel="Proveedor" />
          </div>
          <div>
            <Segmentos<EstadoDoc | "todos"> size="sm" etiqueta="Estado" valor={estado || "todos"} onChange={(v) => setEstado(v === "todos" ? "" : v)}
              opciones={[{ id: "todos", label: "Todos" },
                ...(["decision", "revisar", "pendiente", "aprobado"] as EstadoDoc[])
                  .filter((k) => k === "aprobado" || (cuenta(k)?.cantidad ?? 0) > 0 || estado === k)
                  .map((k) => ({ id: k, label: cuenta(k)?.etiqueta ?? k, aviso: k === "aprobado" ? undefined : cuenta(k)?.cantidad }))]} />
          </div>
          <div className="ml-auto flex items-center gap-2">
            <span className="text-xs text-ink-secondary">Ver por</span>
            <Segmentos<Agrupar> size="sm" etiqueta="Agrupar" valor={agrupar} onChange={setAgrupar}
              opciones={[{ id: "documento", label: "Documento" }, { id: "destino", label: "Destino" }, { id: "proveedor", label: "Proveedor" }]} />
          </div>
        </div>
        {!!d?.porDestino.length && (
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="mr-1 text-xs font-medium text-ink-secondary">Destino</span>
            <button type="button" onClick={() => setDestino("")}
              className={`rounded-full border px-2 py-0.5 text-xs ${!destino ? "border-finance bg-finance-light text-finance" : "border-border text-ink-secondary hover:bg-surface-sunken"}`}>Todos</button>
            {d.porDestino.slice(0, 10).map((x) => (
              <button key={x.clave} type="button" onClick={() => setDestino(destino === x.clave ? "" : x.clave)}
                className={`rounded-full ${destino === x.clave ? "ring-2 ring-finance/50" : "opacity-90 hover:opacity-100"}`} title={`${x.cantidad} documentos · ${formatMoneda(x.importe)}`}>
                <ChipDestino d={{ ...x, porcentaje: null }} />
              </button>
            ))}
            {d.porDestino.length > 10 && (
              <select aria-label="Más destinos" className="rounded-full border border-border bg-surface px-2 py-0.5 text-xs text-ink-secondary"
                value={d.porDestino.slice(10).some((x) => x.clave === destino) ? destino : ""} onChange={(e) => setDestino(e.target.value)}>
                <option value="">+{d.porDestino.length - 10} más…</option>
                {d.porDestino.slice(10).map((x) => <option key={x.clave} value={x.clave}>{x.etiqueta}</option>)}
              </select>
            )}
          </div>
        )}
      </section>

      {corridasElegidas.length > 0 && (
        <div className="sticky top-16 z-10 flex items-center justify-between rounded-lg border border-finance/40 bg-finance-light px-4 py-2 text-sm shadow">
          <span>{elegidos.size} documento{elegidos.size === 1 ? "" : "s"} elegido{elegidos.size === 1 ? "" : "s"}</span>
          <span className="flex gap-2">
            <Button size="sm" variant="ghost" onClick={() => setElegidos(new Set())}>Cancelar</Button>
            <Button size="sm" variant="primary" disabled={aprobar.isPending} onClick={() => aprobar.mutate(corridasElegidas)}>{aprobar.isPending ? "Aprobando…" : "Aprobar elegidos"}</Button>
          </span>
        </div>
      )}
      {seleccionables.length > 0 && !corridasElegidas.length && (
        <button type="button" className="text-xs font-medium text-finance hover:underline" onClick={() => setElegidos(new Set(seleccionables.map((r) => r.idCompra)))}>
          Elegir los {seleccionables.length} pendientes de esta página</button>
      )}

      {q.isLoading ? <LoadingState rows={8} /> : q.isError ? <ErrorState message="No se pudo leer la imputación." onRetry={() => q.refetch()} /> : agrupar === "documento" ? (
        <>
          <DataTable columns={columnas} rows={d?.items ?? []} keyField={(r) => r.idCompra} layout="fixed" stickyHeader
            emptyMessage="No hay documentos con estos filtros." page={page} pageSize={TAM} total={d?.total ?? 0} onPageChange={setPage}
            onRowClick={setAbierto} selectedKey={abierto?.idCompra ?? null}
            rowActions={(r) => [{ label: "Ver detalle", onClick: () => setAbierto(r) }, { label: "Abrir la compra", href: `/compras/${r.idCompra}/editar` }]} />
          {!!d?.total && <p className="text-right text-sm text-ink-secondary">{formatCantidad(d.total)} documentos · total con estos filtros <strong className="font-data text-ink-primary">{formatMoneda(d.importe)}</strong></p>}
        </>
      ) : agrupar === "destino" ? (
        <TablaGrupo filas={(d?.porDestino ?? []).map((x) => ({ k: x.clave, nombre: <ChipDestino d={{ ...x, porcentaje: null }} />, cantidad: x.cantidad, importe: x.importe }))}
          total={d?.importe ?? 0} titulo="Destino" onElegir={(k) => { setDestino(k); setAgrupar("documento"); }} />
      ) : (
        <TablaGrupo filas={(d?.porProveedor ?? []).map((x) => ({ k: String(x.idContacto), nombre: x.proveedor, cantidad: x.cantidad, importe: x.importe, id: x.idContacto, prov: x.proveedor }))}
          total={d?.importe ?? 0} titulo="Proveedor" onElegir={(k) => { const p = d?.porProveedor.find((x) => String(x.idContacto) === k);
            if (p?.idContacto) { setIdContacto(p.idContacto); setProveedor(p.proveedor); } setAgrupar("documento"); }} />
      )}

      <DocumentoDrawer fila={abierto} onClose={() => setAbierto(null)} />
      <ControlDrawer open={control} onClose={() => setControl(false)} />
    </main>
  );
}

function TablaGrupo({ filas, total, titulo, onElegir }: { filas: { k: string; nombre: React.ReactNode; cantidad: number; importe: number }[]; total: number; titulo: string; onElegir: (k: string) => void }) {
  return (
    <div className="overflow-hidden rounded-lg border border-border bg-surface">
      <table className="w-full text-sm">
        <thead className="bg-surface-sunken text-left text-xs text-ink-secondary">
          <tr><th className="px-3 py-2">{titulo}</th><th className="px-3 py-2 text-right">Documentos</th><th className="px-3 py-2 text-right">Importe</th><th className="px-3 py-2 text-right">%</th></tr>
        </thead>
        <tbody className="divide-y divide-border">
          {filas.map((f) => (
            <tr key={f.k} className="cursor-pointer hover:bg-surface-sunken/60" onClick={() => onElegir(f.k)} title="Ver sus documentos">
              <td className="px-3 py-1.5">{f.nombre}</td>
              <td className="px-3 py-1.5 text-right font-data">{formatCantidad(f.cantidad)}</td>
              <td className="px-3 py-1.5 text-right font-data">{formatMoneda(f.importe)}</td>
              <td className="px-3 py-1.5 text-right font-data text-ink-secondary">{total ? `${formatCantidad(Math.round((f.importe / total) * 1000) / 10)}%` : ""}</td>
            </tr>
          ))}
        </tbody>
        <tfoot className="border-t border-border font-medium"><tr><td className="px-3 py-2">Total</td><td /><td className="px-3 py-2 text-right font-data">{formatMoneda(total)}</td><td /></tr></tfoot>
      </table>
    </div>
  );
}

export default function DocumentosImputacionPage() {
  return <Suspense><Pagina /></Suspense>;
}
