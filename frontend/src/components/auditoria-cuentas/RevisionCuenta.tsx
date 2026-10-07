"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRef, useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { OrigenMovimiento } from "@/components/cuentas-corrientes/OrigenMovimiento";
import { ReasignarMovimientoButton } from "@/components/cuentas-corrientes/ReasignarMovimientoButton";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { BASE_DOCUMENTOS_COMPRAS, esRutaLocalWindows, urlParaAbrirDocumento } from "@/lib/documentoLocal";
import { formatFecha, formatMoneda } from "@/lib/format";
import { fetchComprobantes, fetchMovimientosRevision, fetchRevision, guardarRevision, type EstadoRevision, type SugerenciaNota } from "@/services/auditoriaCuentasApi";
import { FifoCuenta } from "./FifoCuenta";
import { HistorialCorrecciones, ImputacionesSospechosas, NotaDeAjuste } from "./CorreccionesCuenta";
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
  const [sugerida, setSugerida] = useState<SugerenciaNota | null>(null);
  const forzar = useRef(false);

  const rev = useQuery({ queryKey: ["auditoria-revision", idContacto], queryFn: () => fetchRevision(idContacto) });
  const movs = useQuery({
    queryKey: ["auditoria-movimientos", idContacto, pagina],
    queryFn: () => {
      const refrescar = forzar.current;
      forzar.current = false;
      return fetchMovimientosRevision(idContacto, pagina, POR_PAGINA, refrescar);
    },
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
    const paginas = Math.max(1, Math.ceil((movs.data?.total ?? 0) / POR_PAGINA));
  const estado = ESTADOS[r.estado];

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">{r.razonSocial ?? `Contacto ${r.idContacto}`}</h1>
          {movs.data?.gobierna === "Dolares" ? (
            <p className="text-sm">
              Saldo en dólares: <b>{formatMoneda(movs.data.saldoDolares, "Dolares")}</b>{" "}
              <span className="text-ink-secondary">(crédito menos deuda; negativo = se le debe) · En pesos: {formatMoneda(movs.data.saldoPesos)}</span>
            </p>
          ) : (
            <p className="text-sm">
              Saldo en pesos: <b>{formatMoneda(movs.data?.saldoPesos ?? r.saldo)}</b>{" "}
              <span className="text-ink-secondary">(crédito menos deuda; negativo = se le debe)</span>
              {movs.data?.tieneDolares && (
                <>
                  {" "}· En dólares: <b>{formatMoneda(movs.data.saldoDolares, "Dolares")}</b>
                </>
              )}
            </p>
          )}
          {movs.data?.gobierna === "Dolares" && (
            <p className="text-xs text-ink-secondary">
              Este proveedor emite sus documentos en dólares: gobierna el dólar. Cada pago en pesos se pasa a dólares con el dólar BNA del día anterior; si el proveedor
              aceptó el pago en pesos al tipo de cambio de su factura, la diferencia que quede es diferencia de cambio y se cierra con una nota de ajuste.
            </p>
          )}
          {movs.data?.gobierna === "Mixta" && (
            <p className="text-xs text-ink-secondary">
              Este proveedor tiene documentos en dólares y en pesos: cada documento gobierna en su moneda. Para saber qué pago cubrió cada documento hay que completar el FIFO de esta
              cuenta; mientras tanto se muestran los dos saldos (en pesos, los documentos en dólares valen lo que decía su factura).
            </p>
          )}
          {movs.data?.avisos.map((a) => (
            <p key={a} className="text-xs text-status-danger">{a}</p>
          ))}
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
                {a.importe != null && !a.sugerencia && <b className="ml-2">{formatMoneda(a.importe)}</b>}
                {a.sugerencia && (
                  <SoloLectura>
                    <button type="button" onClick={() => setSugerida(a.sugerencia ?? null)} className="ml-2 rounded border border-line px-2 py-0.5">
                      Cargar nota de {a.sugerencia.tipo === "credito" ? "crédito" : "débito"} por esta diferencia
                    </button>
                  </SoloLectura>
                )}
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
      <FifoCuenta idContacto={idContacto} />
      <div className="flex flex-wrap items-center gap-2">
        <NotaDeAjuste key={sugerida ? `s-${sugerida.importe}-${sugerida.tipo}` : "normal"} idContacto={idContacto} permiteDolares={movs.data?.tieneDolares ?? false} sugerencia={sugerida} />
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
                <th className="text-right">Importe original</th>
                <th className="text-right">Deuda ($)</th><th className="text-right">Crédito ($)</th><th className="text-right">Saldo ($)</th>
                {movs.data?.tieneDolares && <th className="text-right">Saldo (US$)</th>}
                <th>Origen</th><th>Comprobante</th><th />
              </tr>
            </thead>
            <tbody>
              {movs.data.items.map((m, i) => {
                const ruta = m.origen.tipo === "compra" && m.origen.idCompra != null ? comprobantes.data?.[String(m.origen.idCompra)] : undefined;
                return (
                  <tr key={`${m.origenTipo}-${m.idOrigen}-${i}`} className="border-t border-line">
                    <td className="py-1">
                      {formatFecha(m.fecha)}
                      {m.fechaEntrega && <span className="block text-xs text-ink-secondary" title="El cheque se entregó antes de cobrarse: el dólar se toma del día de la entrega">cheque entregado el {formatFecha(m.fechaEntrega)}</span>}
                    </td>
                    <td>{m.documento ?? "—"}</td>
                    <td>{m.numeroDocumento ?? "—"}</td>
                    <td className="text-right text-xs">
                      {m.moneda === "Dolares" ? (
                        <span title={m.tcEstimado ? "Sin tipo de cambio propio: se estimó con el dólar BNA del día anterior" : undefined}>
                          {formatMoneda(m.deudaOriginal || m.creditoOriginal, "Dolares")} · TC {m.tipoDeCambio != null ? formatMoneda(m.tipoDeCambio) : "?"}{m.tcEstimado ? " (estimado)" : ""}
                        </span>
                      ) : "—"}
                    </td>
                    <td className="text-right text-status-danger">{m.deudaPesos ? formatMoneda(m.deudaPesos) : "—"}</td>
                    <td className="text-right">{m.creditoPesos ? formatMoneda(m.creditoPesos) : "—"}</td>
                    <td className="text-right font-medium">{formatMoneda(m.saldoPesos)}</td>
                    {movs.data?.tieneDolares && <td className="text-right text-xs">{formatMoneda(m.saldoDolares, "Dolares")}</td>}
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
                    <td><ReasignarMovimientoButton origenTipo={m.origenTipo} idOrigen={m.idOrigen} onReasignado={() => { forzar.current = true; refrescar(); }} /></td>
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
