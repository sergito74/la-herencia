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
  actualizarItems,
  aplicarLote,
  crearLote,
  decidirProveedor,
  descartarLote,
  fetchDetalleProveedor,
  fetchLote,
  fetchLotes,
  fetchProveedoresLote,
  revertirLote,
  type FacturaRevision,
  type PagoFactura,
  type ProveedorLote,
} from "@/services/integridadVinculosApi";

const ESTADO_TONO: Record<ProveedorLote["estado"], BadgeTone> = {
  pendiente: "neutral",
  aprobado: "success",
  rechazado: "warning",
};
const ESTADO_TEXTO: Record<ProveedorLote["estado"], string> = {
  pendiente: "Pendiente",
  aprobado: "Aprobado",
  rechazado: "Queda como está",
};
const CAMBIO_TONO: Record<PagoFactura["cambio"], BadgeTone> = {
  "se mantiene": "neutral",
  "se quita": "danger",
  "se agrega": "success",
  "se pesifica": "warning",
};

function mensaje(e: unknown): string {
  return e instanceof ApiError ? e.message : "Error inesperado.";
}

function money(v: number | null | undefined) {
  return v === null || v === undefined ? "—" : formatMoneda(v);
}

function Saldo({ valor }: { valor: number | null }) {
  if (valor === null) return <span>—</span>;
  const tono = Math.abs(valor) < 1 ? "text-status-success" : valor < 0 ? "text-status-danger" : "text-ink-primary";
  return <span className={tono}>{Math.abs(valor) < 1 ? "pagada" : money(valor)}</span>;
}

function Factura({ f }: { f: FacturaRevision }) {
  return (
    <div className="rounded-md border border-border">
      <div className="flex flex-wrap items-baseline justify-between gap-2 bg-surface-sunken px-3 py-2 text-sm">
        <span className="font-medium">
          {f.numero} · {formatFecha(f.fecha)} · total {money(f.total)}
          {f.moneda === "Dolares" && f.totalOriginal !== null && (
            <span className="text-ink-secondary">
              {" "}
              ({formatMoneda(f.totalOriginal, "Dolares")} × TC {f.tc})
            </span>
          )}
        </span>
        <span className="text-xs">
          Pagado hoy <strong>{money(f.pagadoAntes)}</strong> (saldo <Saldo valor={f.saldoAntes} />) → después{" "}
          <strong>{money(f.pagadoDespues)}</strong> (saldo <Saldo valor={f.saldoDespues} />)
        </span>
      </div>
      <table className="w-full text-sm">
        <thead className="text-left text-xs text-ink-secondary">
          <tr>
            <th className="px-3 py-1">Cambio</th>
            <th className="px-3 py-1">Pago</th>
            <th className="px-3 py-1">Fecha</th>
            <th className="px-3 py-1">Concepto</th>
            <th className="px-3 py-1 text-right">Importe del pago</th>
            <th className="px-3 py-1 text-right">Imputado hoy</th>
            <th className="px-3 py-1 text-right">Imputado después</th>
          </tr>
        </thead>
        <tbody>
          {f.pagos.map((p, i) => (
            <tr key={i} className="border-t border-border align-top">
              <td className="px-3 py-1.5">
                <StatusBadge label={p.cambio} tone={CAMBIO_TONO[p.cambio]} />
              </td>
              <td className="px-3 py-1.5">
                {p.medio}
                <span className="block text-xs text-ink-secondary">{p.via}</span>
              </td>
              <td className="px-3 py-1.5">{formatFecha(p.fecha)}</td>
              <td className="px-3 py-1.5">
                {p.concepto || "—"}
                {p.motivo && <span className="block text-xs text-status-warning">{p.motivo}</span>}
              </td>
              <td className="font-data px-3 py-1.5 text-right">{money(p.importe)}</td>
              <td className="font-data px-3 py-1.5 text-right">{p.cambio === "se agrega" ? "—" : money(p.imputado)}</td>
              <td className="font-data px-3 py-1.5 text-right">
                {money(p.imputadoDespues === null ? p.imputado : p.imputadoDespues)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DetalleProveedorPanel({ idLote, proveedor, editable, onCerrar }: {
  idLote: number;
  proveedor: ProveedorLote;
  editable: boolean;
  onCerrar: () => void;
}) {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const q = useQuery({
    queryKey: ["integridad-proveedor", idLote, proveedor.idContacto],
    queryFn: () => fetchDetalleProveedor(idLote, proveedor.idContacto),
  });
  const refrescar = () => {
    qc.invalidateQueries({ queryKey: ["integridad-proveedor", idLote, proveedor.idContacto] });
    qc.invalidateQueries({ queryKey: ["integridad-proveedores", idLote] });
    qc.invalidateQueries({ queryKey: ["integridad-lote", idLote] });
  };
  const m = useMutation({
    mutationFn: async (fn: () => Promise<unknown>) => fn(),
    onSuccess: refrescar,
    onError: (e) => showToast(mensaje(e), "danger"),
  });

  if (q.isLoading) return <LoadingState />;
  if (q.isError || !q.data) return <ErrorState message="No se pudo armar la cuenta del proveedor." onRetry={() => q.refetch()} />;
  const d = q.data;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm">
          {d.facturas.length} facturas con cambios · estado <StatusBadge label={ESTADO_TEXTO[d.estado]} tone={ESTADO_TONO[d.estado]} />
        </p>
        {editable && (
          <SoloLectura>
            <div className="flex gap-2">
              <button
                type="button"
                className="rounded-md border border-border px-3 py-1.5 text-sm"
                onClick={() =>
                  m.mutate(async () => {
                    await decidirProveedor(idLote, d.idContacto, false);
                    onCerrar();
                  })
                }
              >
                Dejar como está
              </button>
              <button
                type="button"
                className="rounded-md bg-finance px-3 py-1.5 text-sm text-white"
                onClick={() =>
                  m.mutate(async () => {
                    await decidirProveedor(idLote, d.idContacto, true);
                    onCerrar();
                  })
                }
              >
                Aprobar este proveedor
              </button>
            </div>
          </SoloLectura>
        )}
      </div>

      {d.reemplazosPorElegir.length > 0 && (
        <section className="space-y-2">
          <h3 className="font-medium">Elegir a qué corresponde ({d.reemplazosPorElegir.length})</h3>
          <p className="text-xs text-ink-secondary">
            Hay más de una opción posible. Si no elegís, ese reemplazo no se aplica (el resto del proveedor sí).
          </p>
          {d.reemplazosPorElegir.map((r) => (
            <div key={r.idItem} className="rounded-md border border-border p-2 text-sm">
              <p>
                {r.motivo} · {money(r.importe)}
              </p>
              {r.candidatos.map((c, n) => (
                <label key={n} className="mt-1 flex items-center gap-2 text-xs">
                  <input
                    type="radio"
                    name={`cand-${r.idItem}`}
                    disabled={!editable}
                    checked={c.elegidoActual}
                    onChange={() => m.mutate(() => actualizarItems(idLote, { elegir: [{ idItem: r.idItem, candidato: n }] }))}
                  />
                  {c.numero ?? `${c.tipoDocumento} ${c.idDocumento}`} ({formatFecha(c.fecha)}) ← {c.pago.medio}{" "}
                  {formatFecha(c.pago.fecha)} «{c.pago.concepto || "—"}» {money(c.pago.importe)} · saldo libre {money(c.libre)}
                </label>
              ))}
            </div>
          ))}
        </section>
      )}

      <section className="space-y-3">
        <h3 className="font-medium">Facturas: hoy y después</h3>
        {d.facturas.map((f) => (
          <Factura key={`${f.tipoDocumento}-${f.idDocumento}`} f={f} />
        ))}
      </section>

      {d.pagosLibres.length > 0 && (
        <section>
          <h3 className="font-medium">Pagos que quedan sin factura ({d.pagosLibres.length})</h3>
          <p className="text-xs text-ink-secondary">
            Se les quita la imputación y no hay otra factura que encaje: vuelven a «Pendiente de aplicar».
          </p>
          <table className="mt-1 w-full text-sm">
            <tbody>
              {d.pagosLibres.map((p, i) => (
                <tr key={i} className="border-t border-border">
                  <td className="px-3 py-1.5">{p.medio}</td>
                  <td className="px-3 py-1.5">{formatFecha(p.fecha)}</td>
                  <td className="px-3 py-1.5">{p.concepto || "—"}</td>
                  <td className="font-data px-3 py-1.5 text-right">{money(p.importe)}</td>
                  <td className="font-data px-3 py-1.5 text-right">libera {money(p.liberado)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}

export function RevisionLote() {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const [abierto, setAbierto] = useState<ProveedorLote | null>(null);
  const [filtro, setFiltro] = useState<ProveedorLote["estado"] | "todos">("todos");
  const lotes = useQuery({ queryKey: ["integridad-lotes"], queryFn: fetchLotes });
  const actual = lotes.data?.[0];
  const idLote = actual?.idLote;
  const lote = useQuery({
    queryKey: ["integridad-lote", idLote],
    queryFn: () => fetchLote(idLote!, "__ninguno__"),
    enabled: idLote !== undefined,
  });
  const provs = useQuery({
    queryKey: ["integridad-proveedores", idLote],
    queryFn: () => fetchProveedoresLote(idLote!),
    enabled: idLote !== undefined,
  });

  const refrescar = () => {
    for (const k of ["integridad-lotes", "integridad-lote", "integridad-proveedores", "integridad-control"]) {
      qc.invalidateQueries({ queryKey: [k] });
    }
  };
  const accion = useMutation({
    mutationFn: async (fn: () => Promise<unknown>) => fn(),
    onSuccess: refrescar,
    onError: (e) => showToast(mensaje(e), "danger"),
  });

  if (lotes.isLoading) return <LoadingState />;
  if (lotes.isError) return <ErrorState message="No se pudieron leer los lotes." onRetry={() => lotes.refetch()} />;

  const generar = (
    <SoloLectura>
      <button
        type="button"
        className="rounded-md bg-finance px-3 py-1.5 text-sm text-white disabled:opacity-50"
        disabled={accion.isPending}
        onClick={() => accion.mutate(() => crearLote())}
      >
        {accion.isPending ? "Generando propuesta…" : "Generar propuesta de corrección"}
      </button>
    </SoloLectura>
  );

  if (!actual || actual.estado === "descartado" || actual.estado === "revertido") {
    return (
      <div className="space-y-3">
        <EmptyState message="No hay un lote de corrección abierto." />
        {generar}
      </div>
    );
  }
  if (!lote.data || !provs.data) return <LoadingState />;
  const d = lote.data;
  const editable = d.estado === "propuesto";
  const lista = provs.data.filter((p) => filtro === "todos" || p.estado === filtro);
  const aprobados = provs.data.filter((p) => p.estado === "aprobado");
  const importeAprobado = aprobados.reduce((s, p) => s + p.importe, 0);
  const importeTotal = provs.data.reduce((s, p) => s + p.importe, 0);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm">
          Lote <strong>#{d.idLote}</strong> · {d.estado} · {aprobados.length} de {provs.data.length} proveedores aprobados (
          {money(importeAprobado)} de {money(importeTotal)})
          {d.backupArchivo && <span className="text-ink-secondary"> · backup {d.backupArchivo}</span>}
        </p>
        <SoloLectura>
          <div className="flex gap-2">
            {editable && (
              <>
                <button
                  type="button"
                  className="rounded-md border border-border px-3 py-1.5 text-sm"
                  onClick={() => window.confirm("¿Descartar esta propuesta?") && accion.mutate(() => descartarLote(d.idLote))}
                >
                  Descartar
                </button>
                <button
                  type="button"
                  className="rounded-md bg-finance px-3 py-1.5 text-sm text-white disabled:opacity-50"
                  disabled={aprobados.length === 0 || accion.isPending}
                  onClick={() =>
                    window.confirm(
                      `Se tomará un backup de WC y se aplicarán los cambios de ${aprobados.length} proveedores aprobados. Los demás quedan como están. ¿Continuar?`
                    ) &&
                    accion.mutate(async () => {
                      const r = await aplicarLote(d.idLote);
                      showToast(`Aplicado: ${r.anuladas} imputaciones quitadas, ${r.creadas} creadas.`, "success");
                    })
                  }
                >
                  {accion.isPending ? "Aplicando…" : `Aplicar lo aprobado (${aprobados.length})`}
                </button>
              </>
            )}
            {d.estado === "aplicado" && (
              <button
                type="button"
                className="rounded-md border border-status-danger px-3 py-1.5 text-sm text-status-danger"
                onClick={() =>
                  window.confirm("Se deshacen todos los cambios de este lote. ¿Revertir?") &&
                  accion.mutate(() => revertirLote(d.idLote))
                }
              >
                Revertir lote
              </button>
            )}
            {d.estado === "aplicado" && generar}
          </div>
        </SoloLectura>
      </div>

      <div className="flex gap-2 text-sm">
        {(["todos", "pendiente", "aprobado", "rechazado"] as const).map((e) => (
          <button
            key={e}
            type="button"
            className={`rounded-md border px-2 py-1 ${filtro === e ? "border-finance text-finance" : "border-border"}`}
            onClick={() => setFiltro(e)}
          >
            {e === "todos" ? "Todos" : ESTADO_TEXTO[e]}
          </button>
        ))}
      </div>

      <table className="w-full text-sm">
        <thead className="bg-surface-sunken text-left text-xs text-ink-secondary">
          <tr>
            <th className="px-3 py-2">Proveedor / cliente</th>
            <th className="px-3 py-2 text-right">Facturas afectadas</th>
            <th className="px-3 py-2 text-right">Cambios</th>
            <th className="px-3 py-2 text-right">Dinero que se mueve</th>
            <th className="px-3 py-2 text-right">Por elegir</th>
            <th className="px-3 py-2">Estado</th>
          </tr>
        </thead>
        <tbody>
          {lista.map((p) => (
            <tr key={p.idContacto} className="cursor-pointer border-t border-border hover:bg-surface-sunken" onClick={() => setAbierto(p)}>
              <td className="px-3 py-1.5 text-finance">{p.nombre}</td>
              <td className="font-data px-3 py-1.5 text-right">{p.facturas}</td>
              <td className="font-data px-3 py-1.5 text-right">{p.cambios}</td>
              <td className="font-data px-3 py-1.5 text-right">{money(p.importe)}</td>
              <td className="font-data px-3 py-1.5 text-right">{p.reemplazosPorElegir || ""}</td>
              <td className="px-3 py-1.5">
                <StatusBadge label={ESTADO_TEXTO[p.estado]} tone={ESTADO_TONO[p.estado]} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <SideDrawer open={abierto !== null} onClose={() => setAbierto(null)} title={abierto?.nombre ?? ""} maxWidthClass="max-w-6xl">
        {abierto && (
          <DetalleProveedorPanel idLote={d.idLote} proveedor={abierto} editable={editable} onCerrar={() => setAbierto(null)} />
        )}
      </SideDrawer>
    </div>
  );
}
