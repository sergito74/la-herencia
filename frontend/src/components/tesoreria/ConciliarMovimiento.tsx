"use client";

import { ConciliacionDocumentos } from "./ConciliacionDocumentos";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

import {
  fetchEstadoConciliacion,
  postConciliacion,
} from "@/services/conciliacionTesoreriaApi";
import { ApiError } from "@/services/apiClient";
import { fetchReferenciaOrigen, type Medio } from "@/services/tesoreriaApi";
import { SoloLectura } from "@/components/auth/SoloLectura";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { MoneyInput } from "@/components/ui/MoneyInput";
import { StatusBadge, type BadgeTone } from "@/components/ui/StatusBadge";
import { useToast } from "@/components/ui/Toast";
import { formatMoneda } from "@/lib/format";

const MEDIOS_CONCILIABLES: Medio[] = [
  "bna",
  "galicia",
  "mercado-libre",
  "efectivo",
  "valores-propios",
  "valores-recibidos",
];

const ETIQUETA_ESTADO: Record<string, { label: string; tone: BadgeTone }> = {
  sin_documento: { label: "Conciliado", tone: "success" },
  sin_conciliar: { label: "Sin conciliar", tone: "neutral" },
  parcialmente_conciliado: { label: "Parcialmente conciliado", tone: "warning" },
  conciliado: { label: "Conciliado", tone: "success" },
  ya_reconocido: { label: "Ya reconocido", tone: "success" },
};

/**
 * Acción de conciliar un movimiento de Tesorería con uno o más contactos
 * (023-conciliacion-tesoreria, US1/US2). Reparto incremental: cada POST
 * aplica la parte cargada en ese momento, el panel queda disponible para
 * seguir agregando contactos mientras quede saldo pendiente (US2). Nunca
 * ofrece conciliar un movimiento `ya_reconocido` (US3, FR-008) — Tarjetas
 * no pasa por este componente en absoluto (FR-002, se filtra en
 * MovimientosPorMedio.tsx).
 */
export function ConciliarMovimiento({
  medio,
  idMovimiento,
  estadoExterno,
  idContacto: idContactoFila,
  contacto: contactoFila,
}: {
  medio: Medio;
  idMovimiento: number;
  // 024-traspasos-internos-tesoreria: `estadoConciliacion` unificado que ya
  // trae la fila del listado — si el movimiento ya está vinculado como
  // traspaso interno, este componente no ofrece conciliar (FR-006, misma
  // guarda simétrica que 023 aplica para `ya_reconocido`).
  estadoExterno?: string | null;
  /** 19/11/2026: contacto que ya trae la fila, para "Ver cuenta" sin consultar el estado. */
  idContacto?: number | null;
  contacto?: string | null;
}) {
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const [modoDocumentos, setModoDocumentos] = useState(true);
  const [abierto, setAbierto] = useState(false);
  const [idContacto, setIdContacto] = useState<number | null>(null);
  const [razonSocial, setRazonSocial] = useState<string | null>(null);
  const [importe, setImporte] = useState(0);
  const [confirmando, setConfirmando] = useState(false);
  const [guardando, setGuardando] = useState(false);

  // 19/11/2026 (auditoría de Tesorería, mejora 1): el listado ya trae el estado de cada fila; el detalle se pide recién
  // cuando se abre un movimiento (antes eran 51 pedidos por página y la columna mostraba "…").
  const [activo, setActivo] = useState(!estadoExterno);
  const [abrirAlCargar, setAbrirAlCargar] = useState(false);
  const estadoQuery = useQuery({
    queryKey: ["conciliacion-estado", medio, idMovimiento],
    queryFn: () => fetchEstadoConciliacion(medio, idMovimiento),
    enabled: MEDIOS_CONCILIABLES.includes(medio) && activo,
  });
  useEffect(() => {
    if (abrirAlCargar && estadoQuery.data) {
      setAbrirAlCargar(false);
      setImporte(estadoQuery.data.saldoPendiente);
      setAbierto(true);
    }
  }, [abrirAlCargar, estadoQuery.data]);

  const referenciaQuery = useQuery({
    queryKey: ["conciliacion-referencia", medio, idMovimiento],
    queryFn: () => fetchReferenciaOrigen(medio, idMovimiento),
    enabled: abierto && estadoQuery.data?.estado !== "ya_reconocido" && estadoQuery.data?.estado !== "conciliado",
  });

  if (!MEDIOS_CONCILIABLES.includes(medio)) {
    return <span className="text-xs text-ink-secondary">—</span>;
  }
  if (estadoExterno === "traspaso_interno") {
    return <span className="text-xs text-ink-secondary">—</span>;
  }
  if (!activo && estadoExterno) {
    const b = ETIQUETA_ESTADO[estadoExterno] ?? { label: estadoExterno, tone: "neutral" as BadgeTone };
    const abrir = () => { setActivo(true); setAbrirAlCargar(true); };
    if (estadoExterno === "ya_reconocido") {
      return (
        <div className="flex items-center gap-2">
          <StatusBadge label={b.label} tone={b.tone} />
          {idContactoFila ? (
            <Link href={`/finanzas/cuentas-corrientes?idContacto=${idContactoFila}&razonSocial=${encodeURIComponent(contactoFila ?? "")}`}
              className="text-xs text-finance underline" title={contactoFila ? `Cuenta de ${contactoFila}` : undefined}>Ver cuenta</Link>
          ) : (
            <button type="button" className="text-xs text-finance underline" onClick={() => setActivo(true)}>Ver cuenta</button>
          )}
        </div>
      );
    }
    const conciliado = estadoExterno === "conciliado" || estadoExterno === "sin_documento";
    return (
      <SoloLectura>
        <div className="flex items-center gap-2">
          <StatusBadge label={b.label} tone={b.tone} />
          <button type="button" className="text-xs text-finance underline" onClick={abrir}>{conciliado ? "Ver / corregir" : "Conciliar"}</button>
        </div>
      </SoloLectura>
    );
  }
  if (estadoQuery.isError) {
    return <button type="button" className="text-xs text-status-danger underline" onClick={() => estadoQuery.refetch()}>No se pudo leer la conciliación. Reintentar</button>;
  }
  if (estadoQuery.isLoading || !estadoQuery.data) {
    return <span className="text-xs text-ink-secondary">…</span>;
  }

  const estado = estadoQuery.data;
  const badge = ETIQUETA_ESTADO[estado.estado] ?? { label: estado.estado, tone: "neutral" as BadgeTone };

  function refrescar() {
    queryClient.invalidateQueries({ queryKey: ["conciliacion-estado", medio, idMovimiento] });
    queryClient.invalidateQueries({ queryKey: ["tesoreria-movimientos"] });
    queryClient.invalidateQueries({ queryKey: ["cc-saldo"] });
    queryClient.invalidateQueries({ queryKey: ["cc-movimientos"] });
    queryClient.invalidateQueries({ queryKey: ["cc-saldos"] });
  }

  function abrirPanel() {
    setImporte(estado.saldoPendiente);
    setAbierto(true);
  }

  function usarCandidata(idContactoCandidata: number | null, nombre: string | null, importeCandidata: number | null) {
    if (idContactoCandidata == null) return;
    setIdContacto(idContactoCandidata);
    setRazonSocial(nombre);
    setImporte(importeCandidata ?? estado.saldoPendiente);
    setConfirmando(true);
  }

  async function confirmar() {
    if (!idContacto || importe <= 0) return;
    setGuardando(true);
    try {
      await postConciliacion(medio, idMovimiento, { idContacto, importe });
      showToast(`Movimiento conciliado a ${razonSocial ?? idContacto} por ${formatMoneda(importe)}.`, "success");
      setConfirmando(false);
      setIdContacto(null);
      setRazonSocial(null);
      // Recalculado acá mismo (no esperar el refetch async) para que, si
      // queda saldo pendiente, el campo Importe ya muestre ese resto y no
      // el valor de la parte recién confirmada (reparto incremental, US2).
      setImporte(Math.max(estado.saldoPendiente - importe, 0));
      refrescar();
      // El panel sigue abierto si queda saldo pendiente (reparto incremental, US2);
      // se cierra solo cuando el movimiento queda conciliado por completo.
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "Error al conciliar el movimiento.", "danger");
    } finally {
      setGuardando(false);
    }
  }

  // 19/11/2026 (Sergio): en la fila solo el estado; motivo, detalle y usuario quedan en "Ver / corregir".
  if (estado.estado === "conciliado" || estado.auditoria) {
    // Aunque ya esté conciliado, el usuario puede haberse equivocado al
    // cargarlo — el panel sigue disponible (en modo solo-documentos, sin
    // pestaña manual) para ver y quitar la imputación mal cargada.
    return (
      <SoloLectura>
        <div className="relative space-y-1">
          <div className="flex items-center gap-2">
            <StatusBadge label={badge.label} tone={badge.tone} />
            <button type="button" onClick={() => (abierto ? setAbierto(false) : setAbierto(true))} className="text-xs text-finance underline">
              {abierto ? "Cerrar" : "Ver / corregir"}
            </button>
          </div>
          {abierto && createPortal(
            <dialog
              ref={node => { if (node && !node.open) node.showModal(); }}
              onCancel={() => setAbierto(false)}
              aria-label="Ver conciliación"
              className="m-auto w-[min(42rem,94vw)] max-h-[90vh] overflow-y-auto space-y-3 rounded-md border border-border bg-surface p-5 text-left text-ink-primary shadow-lg backdrop:bg-black/40"
            >
              <div className="flex items-center justify-between gap-4">
                <h2 className="text-lg font-semibold">Conciliación del movimiento</h2>
                <button type="button" className="text-sm text-finance underline" onClick={() => setAbierto(false)}>Cerrar</button>
              </div>
              <ConciliacionDocumentos medio={medio} idMovimiento={idMovimiento} estado={estado} onSaved={refrescar}/>
            </dialog>, document.body
          )}
        </div>
      </SoloLectura>
    );
  }

  if (estado.estado === "ya_reconocido") {
    return (
      <div className="flex items-center gap-2">
        <StatusBadge label={badge.label} tone={badge.tone} />
        {estado.idContactoReconocido != null && (
          <Link
            href={`/finanzas/cuentas-corrientes?idContacto=${estado.idContactoReconocido}&razonSocial=${encodeURIComponent(estado.contactoReconocido ?? "")}`}
            className="text-xs text-finance underline"
            title={`Cuenta de ${estado.contactoReconocido ?? "—"}. El contacto se reconoce por el origen habitual del movimiento; para corregirlo, reasignalo desde su cuenta corriente.`}
          >
            Ver cuenta
          </Link>
        )}
      </div>
    );
  }

  return (
    <SoloLectura>
      <div className="relative space-y-1">
        <div className="flex items-center gap-2">
          <StatusBadge label={badge.label} tone={badge.tone} />
          {estado.estado === "parcialmente_conciliado" && (
            <span className="text-xs text-ink-secondary">Pendiente: {formatMoneda(estado.saldoPendiente)}</span>
          )}
          <button
            type="button"
            onClick={() => (abierto ? setAbierto(false) : abrirPanel())}
            className="text-xs text-finance underline"
          >
            {abierto ? "Cancelar" : "Conciliar"}
          </button>
        </div>

        {abierto && createPortal(
          <dialog
            ref={node => { if (node && !node.open) node.showModal(); }}
            onCancel={() => setAbierto(false)}
            aria-label="Conciliar movimiento"
            className="m-auto w-[min(42rem,94vw)] max-h-[90vh] overflow-y-auto space-y-3 rounded-md border border-border bg-surface p-5 text-left text-ink-primary shadow-lg backdrop:bg-black/40"
          >
            <div className="flex items-center justify-between gap-4">
              <h2 className="text-lg font-semibold">Conciliar movimiento</h2>
              <button type="button" className="text-sm text-finance underline" onClick={() => setAbierto(false)}>Cerrar</button>
            </div>
            <div className="flex gap-3 border-b border-border pb-2">
              <button type="button" className={modoDocumentos ? "font-bold text-finance" : "underline"} onClick={()=>setModoDocumentos(true)}>Documentos</button>
              <button type="button" className={!modoDocumentos ? "font-bold text-finance" : "underline"} onClick={()=>setModoDocumentos(false)}>Carga manual</button>
            </div>
            {modoDocumentos && <ConciliacionDocumentos medio={medio} idMovimiento={idMovimiento} estado={estado} onSaved={refrescar}/>}
            {!modoDocumentos && !confirmando && (
              <>
                {referenciaQuery.data && referenciaQuery.data.estado !== "sin_coincidencia" && (
                  <div className="space-y-1 rounded border border-border-strong bg-surface-sunken p-2">
                    <p className="text-xs font-medium text-ink-primary">Referencia de origen sugerida:</p>
                    {referenciaQuery.data.candidatas.map((c) => (
                      <button
                        key={c.idCompra}
                        type="button"
                        disabled={c.idContacto == null}
                        className="block w-full rounded border border-border px-2 py-1 text-left text-xs hover:bg-surface disabled:opacity-50"
                        onClick={() => usarCandidata(c.idContacto, c.proveedor, c.importe)}
                      >
                        Compra {c.numeroDocumento ?? "—"} — {c.proveedor ?? "—"}
                        {c.importe != null ? ` — ${formatMoneda(c.importe)}` : ""}
                      </button>
                    ))}
                  </div>
                )}

                <ContactoSelect
                  value={idContacto}
                  razonSocial={razonSocial}
                  onChange={(id, nombre) => {
                    setIdContacto(id);
                    setRazonSocial(nombre);
                  }}
                  placeholder="Buscar contacto…"
                />
                <label className="flex flex-col gap-1 text-xs text-ink-secondary">
                  Importe a conciliar (saldo pendiente: {formatMoneda(estado.saldoPendiente)})
                  <MoneyInput value={importe} onChange={setImporte} moneda="Pesos" />
                </label>
                <div className="flex justify-end">
                  <button
                    type="button"
                    disabled={!idContacto || importe <= 0}
                    onClick={() => setConfirmando(true)}
                    className="rounded-md bg-finance font-medium text-white shadow-sm transition-colors hover:bg-finance/90 disabled:opacity-60 px-2 py-1 text-xs"
                  >
                    Continuar
                  </button>
                </div>
              </>
            )}

            {!modoDocumentos && confirmando && (
              <div className="space-y-2 text-xs">
                <p>
                  ¿Conciliar <strong>{formatMoneda(importe)}</strong> de este movimiento a{" "}
                  <strong>{razonSocial ?? idContacto}</strong>
                  {importe < estado.saldoPendiente ? " (queda un saldo pendiente)" : ""}?
                </p>
                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setConfirmando(false)}
                    className="rounded border border-border px-2 py-1 hover:bg-surface-sunken"
                  >
                    Volver
                  </button>
                  <button
                    type="button"
                    disabled={guardando}
                    onClick={confirmar}
                    className="rounded-md bg-finance font-medium text-white shadow-sm transition-colors hover:bg-finance/90 disabled:opacity-60 px-2 py-1"
                  >
                    {guardando ? "Guardando…" : "Confirmar"}
                  </button>
                </div>
              </div>
            )}
          </dialog>, document.body
        )}
      </div>
    </SoloLectura>
  );
}
