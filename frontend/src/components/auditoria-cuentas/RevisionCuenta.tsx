"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { OrigenMovimiento } from "@/components/cuentas-corrientes/OrigenMovimiento";
import { ReasignarMovimientoButton } from "@/components/cuentas-corrientes/ReasignarMovimientoButton";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { BASE_DOCUMENTOS_COMPRAS, esRutaLocalWindows, urlParaAbrirDocumento } from "@/lib/documentoLocal";
import { formatFecha, formatMoneda } from "@/lib/format";
import { fetchComprobantes, fetchRevision, guardarRevision, type EstadoRevision } from "@/services/auditoriaCuentasApi";
import { HistorialCorrecciones, ImputacionesSospechosas, NotaDeAjuste } from "./CorreccionesCuenta";
import { fetchMovimientos } from "@/services/cuentasCorrientesApi";
import { urlDocumentoLocal } from "@/services/comprasApi";

const ESTADOS: Record<EstadoRevision, { texto: string; clase: string }> = {
  pendiente: { texto: "Pendiente de revisar", clase: "text-ink-secondary" },
  revisada: { texto: "Revisada", clase: "text-status-success" },
  "revision-vieja": { texto: "Revisada, pero el saldo cambió después", clase: "text-status-danger" },
};
const POR_PAGINA = 100;

/** Revisión de una cuenta: movimientos con saldo acumulado, avisos, corrección en el lugar y marca de revisada (035, Historia 0). */
export function RevisionCuenta({ idContacto }: { idContacto: number }) {
  const qc = useQueryClient();
  const [pagina, setPagina] = useState(1);
  const [nota, setNota] = useState("");
  const [verHistorial, setVerHistorial] = useState(false);

  const rev = useQuery({ queryKey: ["auditoria-revision", idContacto], queryFn: () => fetchRevision(idContacto) });
  const movs = useQuery({
    queryKey: ["auditoria-movimientos", idContacto, pagina],
    queryFn: () => fetchMovimientos(idContacto, { page: pagina, pageSize: POR_PAGINA, sortBy: "fecha", sortDir: "desc" }),
  });
  const comprobantes = useQuery({ queryKey: ["auditoria-comprobantes", idContacto], queryFn: () => fetchComprobantes(idContacto) });

  const refrescar = () => {
    for (const k of ["auditoria-revision", "auditoria-movimientos", "auditoria-comprobantes", "auditoria-resumen", "auditoria-grupo"])
      qc.invalidateQueries({ queryKey: [k] });
  };
  const guardar = useMutation({
    mutationFn: (cambio: Parameters<typeof guardarRevision>[1]) => guardarRevision(idContacto, cambio),
    onSuccess: () => {
      setNota("");
      refrescar();
    },
  });

  if (rev.isLoading) return <LoadingState />;
  if (rev.isError || !rev.data) return <ErrorState message="No se pudo cargar la cuenta." onRetry={() => rev.refetch()} />;
  const r = rev.data;
  const moneda = r.moneda === "Dolares" ? "Dolares" : "Pesos";
  const paginas = Math.max(1, Math.ceil((movs.data?.total ?? 0) / POR_PAGINA));
  const estado = ESTADOS[r.estado];

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">{r.razonSocial ?? `Contacto ${r.idContacto}`}</h1>
          <p className="text-sm">
            Saldo: <b>{formatMoneda(r.saldo, moneda)}</b> <span className="text-ink-secondary">(crédito menos deuda; negativo = se le debe)</span>
          </p>
          <p className={`text-xs ${estado.clase}`}>
            {estado.texto}
            {r.fechaRevision && ` — ${formatFecha(r.fechaRevision)} por ${r.usuarioRevision ?? "?"}${r.nota ? `: ${r.nota}` : ""}`}
          </p>
        </div>
        <nav className="flex items-center gap-2 text-sm">
          <span className="text-xs text-ink-secondary">{r.revisadas} de {r.totalCuentas} revisadas</span>
          {r.anterior && (
            <Link className="rounded border border-line px-3 py-1" href={`/finanzas/auditoria-cuentas/cuenta/${r.anterior.idContacto}`}>← {r.anterior.razonSocial}</Link>
          )}
          {r.siguiente ? (
            <Link className="rounded bg-finance px-3 py-1 text-white" href={`/finanzas/auditoria-cuentas/cuenta/${r.siguiente.idContacto}`}>Siguiente: {r.siguiente.razonSocial} →</Link>
          ) : (
            <span className="text-xs text-status-success">No quedan cuentas pendientes</span>
          )}
        </nav>
      </header>

      <section className="rounded border border-line p-3 text-sm">
        <h2 className="text-sm font-semibold">Avisos de esta cuenta</h2>
        {r.avisos.length === 0 ? (
          <p className="text-xs text-status-success">Sin avisos: el saldo y los movimientos cierran.</p>
        ) : (
          <ul className="list-disc pl-5 text-xs">
            {r.avisos.map((a, i) => (
              <li key={i}>
                {a.motivo}
                {a.importe != null && <b className="ml-2">{formatMoneda(a.importe, moneda)}</b>}
              </li>
            ))}
          </ul>
        )}
        <div className="mt-2 flex flex-wrap items-center gap-3 text-xs">
          <label>
            Saldo esperado:{" "}
            <select
              value={r.saldoEsperado ?? ""}
              onChange={(e) => (e.target.value ? guardar.mutate({ saldoEsperado: e.target.value as "cero" | "puede-tener-saldo" }) : guardar.mutate({ quitarSaldoEsperado: true }))}
              className="rounded border border-line px-1 py-0.5"
            >
              <option value="">Sin definir</option>
              <option value="cero">Tiene que ser cero</option>
              <option value="puede-tener-saldo">Puede tener saldo</option>
            </select>
          </label>
          <SoloLectura>
            <input value={nota} onChange={(e) => setNota(e.target.value)} placeholder="Nota (opcional)" aria-label="Nota de la revisión" className="w-64 rounded border border-line px-2 py-1" />
            <button type="button" disabled={guardar.isPending} onClick={() => guardar.mutate({ estado: "revisada", nota })} className="rounded bg-finance px-3 py-1 text-white">
              Marcar como revisada
            </button>
            {r.estado !== "pendiente" && (
              <button type="button" disabled={guardar.isPending} onClick={() => guardar.mutate({ estado: "pendiente" })} className="rounded border border-line px-3 py-1">
                Volver a pendiente
              </button>
            )}
          </SoloLectura>
          {guardar.isError && <span role="alert" className="text-status-danger">No se pudo guardar.</span>}
        </div>
      </section>

      <ImputacionesSospechosas idContacto={idContacto} />
      <div className="flex flex-wrap items-center gap-2">
        <NotaDeAjuste idContacto={idContacto} moneda={moneda === "Dolares" ? "Dolares" : "Pesos"} />
      </div>
      <HistorialCorrecciones idContacto={idContacto} />

      <section>
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">Movimientos (los más nuevos primero)</h2>
          <span className="text-xs text-ink-secondary">{movs.data?.total ?? 0} movimientos · página {pagina} de {paginas}</span>
        </div>
        {movs.isLoading && <LoadingState />}
        {movs.isError && <ErrorState message="No se pudieron cargar los movimientos." onRetry={() => movs.refetch()} />}
        {movs.data && (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-ink-secondary">
                <th className="py-1">Fecha</th><th>Documento</th><th>Nro.</th>
                <th className="text-right">Deuda</th><th className="text-right">Crédito</th><th className="text-right">Saldo</th>
                <th>Origen</th><th>Comprobante</th><th />
              </tr>
            </thead>
            <tbody>
              {movs.data.items.map((m, i) => {
                const ruta = m.origen.tipo === "compra" && m.origen.idCompra != null ? comprobantes.data?.[String(m.origen.idCompra)] : undefined;
                return (
                  <tr key={`${m.origenTipo}-${m.idOrigen}-${i}`} className="border-t border-line">
                    <td className="py-1">{formatFecha(m.fecha)}</td>
                    <td>{m.documento ?? "—"}</td>
                    <td>{m.numeroDocumento ?? "—"}</td>
                    <td className="text-right text-status-danger">{m.deuda ? formatMoneda(m.deuda, moneda) : "—"}</td>
                    <td className="text-right">{m.credito ? formatMoneda(m.credito, moneda) : "—"}</td>
                    <td className="text-right font-medium">{m.saldoParcial != null ? formatMoneda(m.saldoParcial, moneda) : "—"}</td>
                    <td><OrigenMovimiento origen={m.origen} /></td>
                    <td>
                      {ruta ? (
                        <a
                          className="text-xs text-finance underline"
                          href={urlParaAbrirDocumento(ruta, BASE_DOCUMENTOS_COMPRAS, urlDocumentoLocal)}
                          target="_blank"
                          rel="noreferrer"
                          title={esRutaLocalWindows(ruta, BASE_DOCUMENTOS_COMPRAS) ? "Abre el PDF desde el disco de esta PC" : undefined}
                        >
                          Abrir PDF
                        </a>
                      ) : "—"}
                    </td>
                    <td><ReasignarMovimientoButton origenTipo={m.origenTipo} idOrigen={m.idOrigen} onReasignado={refrescar} /></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
        <div className="mt-2 flex items-center gap-2 text-xs">
          <button type="button" disabled={pagina <= 1} onClick={() => setPagina(pagina - 1)} className="rounded border border-line px-2 py-1">← Más nuevos</button>
          <button type="button" disabled={pagina >= paginas} onClick={() => setPagina(pagina + 1)} className="rounded border border-line px-2 py-1">Más viejos →</button>
        </div>
      </section>

      <section className="text-xs">
        <button type="button" className="underline" onClick={() => setVerHistorial(!verHistorial)}>
          {verHistorial ? "Ocultar" : "Ver"} el historial de esta cuenta ({r.historial.length})
        </button>
        {verHistorial && (
          <ul className="mt-1 divide-y divide-line">
            {r.historial.map((h) => (
              <li key={h.id} className="py-1">{formatFecha(h.fecha)} · {h.usuario ?? "?"} · <b>{h.accion}</b> {h.detalle ?? ""}</li>
            ))}
            {r.historial.length === 0 && <li className="py-1 text-ink-secondary">Todavía no hay cambios registrados.</li>}
          </ul>
        )}
      </section>
    </div>
  );
}
