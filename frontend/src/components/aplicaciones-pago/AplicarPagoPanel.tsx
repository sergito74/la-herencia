"use client";

import { useEffect, useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { useToast } from "@/components/ui/Toast";
import { formatMonto } from "@/lib/format";
import {
  anularAplicacion,
  confirmarAplicacion,
  fetchDocumentosPendientes,
  fetchEstadoDocumento,
  fetchSugerencia,
  type DocumentoPendiente,
  type EstadoDocumento,
} from "@/services/aplicacionesPagoApi";

/** Panel de aplicación de un pago/cobro real contra uno o más documentos
 * pendientes (019). Sugiere FIFO al abrir, siempre editable — nunca aplica
 * sin que el usuario confirme (FR-003/FR-004). */
export function AplicarPagoPanel({
  origenMovimiento,
  idMovimientoOrigen,
  onAplicado,
}: {
  origenMovimiento: string;
  idMovimientoOrigen: number;
  onAplicado?: () => void;
}) {
  const { showToast } = useToast();
  const [cargando, setCargando] = useState(true);
  const [filas, setFilas] = useState<{ tipoDocumento: string; idDocumento: number; importeAplicado: string }[]>([]);
  const [saldoSinAsignar, setSaldoSinAsignar] = useState(0);
  const [otroContacto, setOtroContacto] = useState("");
  const [documentosOtroContacto, setDocumentosOtroContacto] = useState<DocumentoPendiente[] | null>(null);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    let activo = true;
    fetchSugerencia(origenMovimiento, idMovimientoOrigen)
      .then((r) => {
        if (!activo) return;
        setFilas(r.sugerencias.map((s) => ({ tipoDocumento: s.tipoDocumento, idDocumento: s.idDocumento, importeAplicado: String(s.importeSugerido) })));
        setSaldoSinAsignar(r.saldoSinAsignar);
      })
      .finally(() => activo && setCargando(false));
    return () => {
      activo = false;
    };
  }, [origenMovimiento, idMovimientoOrigen]);

  async function buscarOtroContacto() {
    const idContacto = Number(otroContacto);
    if (!idContacto) return;
    setDocumentosOtroContacto(await fetchDocumentosPendientes(idContacto));
  }

  function agregarFila(doc: { tipoDocumento: string; idDocumento: number }) {
    setFilas((prev) => [...prev, { tipoDocumento: doc.tipoDocumento, idDocumento: doc.idDocumento, importeAplicado: "0" }]);
  }

  async function confirmar() {
    setEnviando(true);
    try {
      await confirmarAplicacion(
        origenMovimiento,
        idMovimientoOrigen,
        filas.map((f) => ({ tipoDocumento: f.tipoDocumento, idDocumento: f.idDocumento, importeAplicado: Number(f.importeAplicado) }))
      );
      showToast("Aplicación confirmada.", "success");
      onAplicado?.();
    } catch {
      showToast("No se pudo confirmar la aplicación — revisá que no quede ningún documento sobre-aplicado.", "danger");
    } finally {
      setEnviando(false);
    }
  }

  if (cargando) return <p className="text-sm text-ink-secondary">Buscando documentos pendientes…</p>;

  return (
    <div className="space-y-3">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-ink-secondary">
            <th className="py-1.5 pr-2">Documento</th>
            <th className="px-2 py-1.5 text-right">Importe a aplicar</th>
          </tr>
        </thead>
        <tbody>
          {filas.map((f, i) => (
            <tr key={`${f.tipoDocumento}-${f.idDocumento}`} className="border-t border-border">
              <td className="py-1.5 pr-2">
                {f.tipoDocumento} #{f.idDocumento}
              </td>
              <td className="px-2 py-1.5 text-right">
                <input
                  className="w-32 rounded-sm border border-border px-2 py-1 text-right"
                  value={f.importeAplicado}
                  onChange={(e) =>
                    setFilas((prev) => prev.map((row, idx) => (idx === i ? { ...row, importeAplicado: e.target.value } : row)))
                  }
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {saldoSinAsignar > 0 && (
        <p className="text-xs text-status-warning">
          Quedan {formatMonto(saldoSinAsignar)} sin asignar a ningún documento (no hay más facturas pendientes de este
          contacto, o el pago excede lo que debe).
        </p>
      )}

      {/* FR-006: aplicar a un contacto distinto al del movimiento */}
      <details className="rounded-md border border-border p-2">
        <summary className="cursor-pointer text-xs text-ink-secondary">Aplicar a otro contacto…</summary>
        <div className="mt-2 flex items-center gap-2">
          <input
            className="rounded-sm border border-border px-2 py-1 text-sm"
            placeholder="Id de contacto"
            value={otroContacto}
            onChange={(e) => setOtroContacto(e.target.value)}
          />
          <button type="button" onClick={buscarOtroContacto} className="rounded-md border border-border px-2 py-1 text-xs">
            Buscar
          </button>
        </div>
        {documentosOtroContacto && (
          <p className="mt-2 text-xs text-status-warning">
            Estos documentos son de un contacto distinto al del movimiento — se aplicarán igual, marcados como tal.
          </p>
        )}
        <ul className="mt-1 space-y-1">
          {documentosOtroContacto?.map((d) => (
            <li key={`${d.tipoDocumento}-${d.idDocumento}`} className="flex items-center justify-between text-xs">
              <span>
                {d.tipoDocumento} #{d.idDocumento} — saldo {formatMonto(d.saldoPendiente)}
              </span>
              <button type="button" onClick={() => agregarFila(d)} className="underline">
                Agregar
              </button>
            </li>
          ))}
        </ul>
      </details>

      <SoloLectura>
        <button
          type="button"
          onClick={confirmar}
          disabled={enviando || filas.length === 0}
          className="rounded-md border border-agro px-3 py-1.5 text-sm text-agro disabled:opacity-60"
        >
          {enviando ? "Confirmando…" : "Confirmar aplicación"}
        </button>
      </SoloLectura>
    </div>
  );
}

/** Estado de un documento (Pendiente/Parcial/Total) con su historial —
 * incluye aplicaciones anuladas, nunca las oculta (FR-005/User Story 3). */
export function EstadoDocumentoPanel({ tipoDocumento, idDocumento }: { tipoDocumento: string; idDocumento: number }) {
  const [estado, setEstado] = useState<EstadoDocumento | null>(null);
  const { showToast } = useToast();

  useEffect(() => {
    fetchEstadoDocumento(tipoDocumento, idDocumento).then(setEstado);
  }, [tipoDocumento, idDocumento]);

  async function anular(idAplicacion: number) {
    const motivo = window.prompt("Motivo de la anulación:");
    if (!motivo) return;
    await anularAplicacion(idAplicacion, motivo);
    showToast("Aplicación anulada.", "success");
    setEstado(await fetchEstadoDocumento(tipoDocumento, idDocumento));
  }

  if (!estado) return null;

  return (
    <div className="space-y-2 text-sm">
      <p>
        <span className="font-medium">{estado.estado}</span> — aplicado {formatMonto(estado.aplicado)} de{" "}
        {formatMonto(estado.importeTotal)} (saldo {formatMonto(estado.saldoPendiente)})
      </p>
      <ul className="space-y-1">
        {estado.aplicaciones.map((a) => (
          <li key={a.idAplicacion} className={`flex items-center justify-between text-xs ${a.anulada ? "text-ink-secondary line-through" : ""}`}>
            <span>
              {new Date(a.fecha).toLocaleDateString("es-AR")} · {formatMonto(a.importeAplicado)} · {a.usuario}
              {a.anulada && ` (anulada: ${a.motivoAnulacion})`}
            </span>
            {!a.anulada && (
              <SoloLectura>
                <button type="button" onClick={() => anular(a.idAplicacion)} className="underline">
                  Anular
                </button>
              </SoloLectura>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
