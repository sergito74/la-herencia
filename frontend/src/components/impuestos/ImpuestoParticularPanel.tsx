"use client";

// 041 — sección «A cargo de socio» de la ficha de la boleta. La boleta y su
// pago al organismo no cambian: solo se carga el Debe en la cuenta del socio.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { ApiError, apiGet } from "@/services/apiClient";
import {
  anularCargaParticular,
  anularDevolucion,
  crearCargaParticular,
  fetchParticular,
  registrarDevolucion,
  type CargaInput,
} from "@/services/impuestosApi";
import { formatMonto, parseNumeroLocal } from "@/lib/format";

const ESTADO: Record<string, string> = { devuelto: "Devuelto", parcial: "Devuelto parcial", pendiente: "Pendiente de devolución" };

function mensaje(e: unknown): string {
  return e instanceof Error ? e.message : "Error inesperado";
}

export function ImpuestoParticularPanel({ idImpuesto, soloLectura = false }: { idImpuesto: number; soloLectura?: boolean }) {
  const qc = useQueryClient();
  const { data, error } = useQuery({ queryKey: ["impuesto-particular", idImpuesto], queryFn: () => fetchParticular(idImpuesto) });
  const { data: socios } = useQuery({
    queryKey: ["cuentas-socios"],
    queryFn: () => apiGet<{ socios: { idSocio: number; nombre: string }[] }>("/api/cuentas-socios"),
  });

  const [idSocio, setIdSocio] = useState("");
  const [modo, setModo] = useState<"importe" | "porcentaje">("importe");
  const [valor, setValor] = useState("");
  const [motivo, setMotivo] = useState("");
  const [partida, setPartida] = useState("");
  // La clave se conserva entre reintentos (idempotencia) y se renueva al crear.
  const [clave, setClave] = useState(() => crypto.randomUUID());
  const [aviso, setAviso] = useState<{ texto: string; confirmar: Partial<CargaInput> } | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const refrescar = () => {
    qc.invalidateQueries({ queryKey: ["impuesto-particular", idImpuesto] });
    qc.invalidateQueries({ queryKey: ["impuestos"] });
  };

  const crear = useMutation({
    mutationFn: (extra: Partial<CargaInput>) => {
      const n = String(parseNumeroLocal(valor));
      return crearCargaParticular(idImpuesto, {
        claveIdempotencia: clave,
        idSocio: Number(idSocio),
        motivo,
        partida: partida || null,
        ...(modo === "importe" ? { importe: n } : { porcentaje: n }),
        ...extra,
      });
    },
    onSuccess: () => {
      setValor(""); setMotivo(""); setPartida(""); setAviso(null); setErr(null);
      setClave(crypto.randomUUID());
      refrescar();
    },
    onError: (e) => {
      const d = e instanceof ApiError ? e.detalle : undefined;
      if (d?.requiereConfirmacion) {
        const avisos = (d.avisos ?? []) as { codigo: string; mensaje: string; candidatos?: { idMovimiento: number; fecha: string; importe: string }[] }[];
        const confirmar: Partial<CargaInput> = { ...(aviso?.confirmar ?? {}) };
        const textos = avisos.map((a) => {
          if (a.codigo === "CUENTA_CERRADA") confirmar.confirmarCuentaCerrada = true;
          if (a.codigo === "DEBE_MANUAL_EQUIVALENTE" && a.candidatos?.length) {
            const m = a.candidatos[0];
            confirmar.reemplazarMovimientoManual = m.idMovimiento;
            return `${a.mensaje} Se reemplazará el movimiento ${m.idMovimiento} (${m.fecha}, $${formatMonto(Number(m.importe))}).`;
          }
          return a.mensaje;
        });
        setAviso({ texto: textos.join(" "), confirmar });
      } else setErr(mensaje(e));
    },
  });

  const accion = useMutation({
    mutationFn: (f: () => Promise<unknown>) => f(),
    onSuccess: () => { setErr(null); refrescar(); },
    onError: (e) => setErr(mensaje(e)),
  });

  if (error) return <p className="text-sm text-red-600">No se pudo cargar «A cargo de socio».</p>;
  if (!data) return null;

  const pedirMotivo = (titulo: string) => window.prompt(titulo)?.trim() || null;

  return (
    <section className="mt-8 rounded border p-4">
      <h2 className="mb-2 text-lg font-semibold">A cargo de socio</h2>
      <p className="mb-3 text-sm text-gray-600">
        Importe ${formatMonto(Number(data.importe))} · a cargo de socios ${formatMonto(Number(data.aCargoDeSocios))} · parte empresa $
        {formatMonto(Number(data.parteEmpresa))}
      </p>
      {data.avisos.map((a, i) => (
        <p key={i} className="mb-2 text-sm text-amber-700">
          Partida {a.partida}: {a.estado === "ambigua" ? "cargada a varios socios" : `habitualmente a cargo de ${a.socio ?? "—"}`}
          {a.titularOscar ? " (titular Oscar → Condominio)" : ""}
        </p>
      ))}

      {data.cargas.length > 0 && (
        <table className="mb-4 w-full text-sm">
          <thead><tr className="text-left"><th>Socio</th><th className="text-right">Importe</th><th>Motivo</th><th>Partida</th><th>Estado</th><th className="text-right">Devuelto</th><th /></tr></thead>
          <tbody>
            {data.cargas.map((c) => (
              <tr key={c.idCarga} className={c.estado === "anulada" ? "text-gray-400 line-through" : ""}>
                <td>{c.socio}</td>
                <td className="text-right">${formatMonto(Number(c.importe))}</td>
                <td>{c.motivo}</td>
                <td>{c.partida ?? ""}</td>
                <td>{c.estado === "anulada" ? "Anulada" : ESTADO[c.estadoDevolucion ?? ""] ?? ""}</td>
                <td className="text-right">
                  ${formatMonto(Number(c.devuelto))}
                  {c.devoluciones.filter((v) => v.estado === "vigente").map((v) => (
                    <div key={v.idVinculo} className="text-xs text-gray-500">
                      mov. {v.idMovimientoSocio} ${formatMonto(Number(v.importe))}{" "}
                      {!soloLectura && (
                        <button type="button" className="underline" onClick={() => {
                          const m = pedirMotivo("Motivo para quitar la devolución");
                          if (m) accion.mutate(() => anularDevolucion(c.idCarga, v.idVinculo, m));
                        }}>quitar</button>
                      )}
                    </div>
                  ))}
                </td>
                <td className="space-x-2 text-right">
                  {!soloLectura && c.estado === "vigente" && Number(c.pendienteNominal) > 0 && (
                    <button type="button" className="underline" onClick={() => {
                      const mov = window.prompt("Nº de movimiento Haber existente (vacío = registrar devolución nueva)");
                      if (mov === null) return;
                      const imp = window.prompt("Importe devuelto", formatMonto(Number(c.pendienteNominal)));
                      if (!imp) return;
                      const importe = String(parseNumeroLocal(imp));
                      const claveDev = crypto.randomUUID();
                      if (mov.trim()) {
                        accion.mutate(() => registrarDevolucion(c.idCarga, { claveIdempotencia: claveDev, idMovimientoSocio: Number(mov), importe }));
                      } else {
                        const fecha = window.prompt("Fecha (AAAA-MM-DD)");
                        const m = fecha && pedirMotivo("Motivo de la devolución");
                        if (fecha && m) accion.mutate(() => registrarDevolucion(c.idCarga, { claveIdempotencia: claveDev, fecha, importe, motivo: m }));
                      }
                    }}>devolución</button>
                  )}
                  {!soloLectura && c.estado === "vigente" && (
                    <button type="button" className="text-red-600 underline" onClick={() => {
                      const m = pedirMotivo("Motivo de la anulación");
                      if (m) accion.mutate(() => anularCargaParticular(c.idCarga, m));
                    }}>anular</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {!soloLectura && (
        <form
          className="flex flex-wrap items-end gap-2 text-sm"
          onSubmit={(e) => { e.preventDefault(); setErr(null); crear.mutate({}); }}
        >
          <label className="flex flex-col">Socio
            <select className="rounded border px-2 py-1" value={idSocio} onChange={(e) => setIdSocio(e.target.value)} required>
              <option value="">—</option>
              {socios?.socios.map((s) => <option key={s.idSocio} value={s.idSocio}>{s.nombre}</option>)}
            </select>
          </label>
          <label className="flex flex-col">
            <select className="rounded border px-1 py-1" value={modo} onChange={(e) => setModo(e.target.value as "importe" | "porcentaje")}>
              <option value="importe">Importe $</option>
              <option value="porcentaje">Porcentaje %</option>
            </select>
            <input className="w-32 rounded border px-2 py-1 text-right" inputMode="decimal" value={valor} onChange={(e) => setValor(e.target.value)} required />
          </label>
          <label className="flex flex-col">Motivo
            <input className="w-64 rounded border px-2 py-1" value={motivo} onChange={(e) => setMotivo(e.target.value)} required />
          </label>
          <label className="flex flex-col">Partida (opcional)
            <input className="w-36 rounded border px-2 py-1" value={partida} onChange={(e) => setPartida(e.target.value)} />
          </label>
          <button type="submit" disabled={crear.isPending} className="rounded bg-blue-600 px-3 py-1 text-white disabled:opacity-50">
            Cargar a socio
          </button>
        </form>
      )}
      {aviso && (
        <div className="mt-3 rounded border border-amber-400 bg-amber-50 p-2 text-sm">
          {aviso.texto}{" "}
          <button type="button" className="ml-2 underline" onClick={() => crear.mutate(aviso.confirmar)}>Confirmar y cargar</button>
          <button type="button" className="ml-2 underline" onClick={() => setAviso(null)}>Cancelar</button>
        </div>
      )}
      {err && <p className="mt-2 text-sm text-red-600">{err}</p>}
    </section>
  );
}
