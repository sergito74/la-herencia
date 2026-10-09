"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { formatFecha, formatMoneda } from "@/lib/format";
import { fetchRevision } from "@/services/auditoriaCuentasApi";
import {
  revisionCuentasApi,
  type Cola,
  type Criterio,
  type Etapa,
  type EstadoEfectivo,
  type FuenteInventario,
} from "@/services/revisionCuentasApi";

const ETAPAS: { codigo: Etapa; nombre: string }[] = [
  { codigo: "E0", nombre: "Fuentes" },
  { codigo: "E1", nombre: "Documentos" },
  { codigo: "E2", nombre: "Movimientos" },
  { codigo: "E3", nombre: "Tarjetas" },
  { codigo: "E4", nombre: "Evidencia" },
  { codigo: "E5", nombre: "FIFO" },
  { codigo: "E6", nombre: "Cierre" },
];

const NOMBRE_COLA: Record<Cola, string> = {
  A: "Ya sana",
  B: "Solo imputación",
  C: "Doble conteo con tarjeta",
  D: "Pago sin factura",
  E: "Contacto duplicado o movimiento sin contacto",
  F: "Dólares y mixtas",
  G: "Retenciones e impuestos",
  H: "Socios, entidades y compras particulares",
  I: "Excepciones",
};

const NOMBRE_ESTADO: Record<EstadoEfectivo, string> = {
  pendiente: "Pendiente",
  "en-proceso": "En proceso",
  "esperando-evidencia": "Esperando evidencia",
  "esperando-sergio": "Esperando a Sergio",
  cerrada: "Cerrada",
  "cerrada-con-excepcion": "Cerrada con excepción",
  reabierta: "Reabierta (cambió el saldo al corte)",
};

const FUENTES_INVENTARIO: { tipo: FuenteInventario["tipo"]; nombre: string }[] = [
  { tipo: "estado-proveedor", nombre: "Estado de cuenta del proveedor" },
  { tipo: "extracto", nombre: "Extractos del banco" },
  { tipo: "resumen-tarjeta", nombre: "Resúmenes de tarjeta" },
  { tipo: "certificado", nombre: "Certificados de retención" },
  { tipo: "dropbox", nombre: "Comprobantes en Dropbox" },
  { tipo: "access", nombre: "Referencia del Access" },
];

function EstadoCriterio({ c }: { c: Criterio }) {
  if (c.cumple === null) return <span className="text-ink-secondary">No aplica</span>;
  return c.cumple ? <span className="text-status-success">Cumple</span> : <span className="text-status-danger">Falta</span>;
}

/**
 * Diferencia de cambio de una cuenta en dólares o mixta (cola F): se ajusta con una nota de crédito o débito. El aviso y la nota
 * sugerida son los de la auditoría 035; la nota se carga en "Nota de ajuste", más abajo en esta misma pantalla.
 */
function DiferenciaDeCambio({ idContacto }: { idContacto: number }) {
  const { data } = useQuery({ queryKey: ["auditoria-revision", idContacto], queryFn: () => fetchRevision(idContacto) });
  const avisos = (Array.isArray(data?.avisos) ? data.avisos : []).filter((a) => a.tipo === "diferencia-de-cambio");
  if (avisos.length === 0) return null;
  return (
    <div className="rounded border border-line p-2">
      <p className="mb-1 font-medium">Diferencia de cambio</p>
      {avisos.map((a, i) => (
        <p key={i}>
          {a.motivo}
          {a.sugerencia && (
            <> Nota sugerida: de {a.sugerencia.tipo === "credito" ? "crédito" : "débito"} por {formatMoneda(a.sugerencia.importe, "Dolares")}. La aprobás vos al cargarla en &quot;Nota de ajuste&quot;.</>
          )}
        </p>
      ))}
    </div>
  );
}

/** Inventario de fuentes (etapa E0): qué evidencia hay para esta cuenta. */
function Inventario({ idContacto, alGuardar }: { idContacto: number; alGuardar: () => void }) {
  const [marcadas, setMarcadas] = useState<Record<string, boolean>>({ access: true });
  const [error, setError] = useState<string | null>(null);
  const guardar = useMutation({
    mutationFn: () =>
      revisionCuentasApi.confirmarInventario(
        idContacto,
        FUENTES_INVENTARIO.map((f) => ({ tipo: f.tipo, disponible: Boolean(marcadas[f.tipo]) })),
      ),
    onSuccess: () => { setError(null); alGuardar(); },
    onError: (e) => setError(e instanceof Error ? e.message : "No se pudo guardar el inventario."),
  });
  return (
    <div className="space-y-1">
      <p>Marcá la evidencia que tenés para esta cuenta:</p>
      <ul className="grid gap-1 sm:grid-cols-2">
        {FUENTES_INVENTARIO.map((f) => (
          <li key={f.tipo}>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={Boolean(marcadas[f.tipo])} onChange={(e) => setMarcadas({ ...marcadas, [f.tipo]: e.target.checked })} />
              {f.nombre}
            </label>
          </li>
        ))}
      </ul>
      {error && <p role="alert" className="text-status-danger">{error}</p>}
      <button type="button" disabled={guardar.isPending} onClick={() => guardar.mutate()} className="rounded border border-line px-3 py-1">
        {guardar.isPending ? "Guardando…" : "Confirmar inventario"}
      </button>
    </div>
  );
}

/** Decisiones registradas de la cuenta y alta de una nueva. */
function Decisiones({ idContacto }: { idContacto: number }) {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["revision-decisiones", idContacto], queryFn: () => revisionCuentasApi.decisiones(idContacto) });
  const decisiones = Array.isArray(data) ? data : [];
  const [abierta, setAbierta] = useState(false);
  const [tipo, setTipo] = useState<"descartar-access" | "cierre-con-excepcion" | "otro">("otro");
  const [texto, setTexto] = useState("");
  const [evidencia, setEvidencia] = useState("");
  const [error, setError] = useState<string | null>(null);
  const alta = useMutation({
    mutationFn: () => revisionCuentasApi.registrarDecision(idContacto, { tipo, texto: texto.trim(), evidencia: evidencia.trim() || null }),
    onSuccess: () => {
      setAbierta(false); setTexto(""); setEvidencia(""); setError(null);
      qc.invalidateQueries({ queryKey: ["revision-decisiones", idContacto] });
      qc.invalidateQueries({ queryKey: ["revision-ficha", idContacto] });
    },
    onError: (e) => setError(e instanceof Error ? e.message : "No se pudo registrar la decisión."),
  });
  return (
    <div className="space-y-1">
      <h3 className="font-medium">Decisiones</h3>
      {decisiones.length === 0 && <p className="text-ink-secondary">Todavía no hay decisiones registradas.</p>}
      <ul className="space-y-1">
        {decisiones.map((d) => (
          <li key={d.idDecision} className="rounded border border-line p-2">
            <b>{d.tipo === "descartar-access" ? "Descartar el Access" : d.tipo === "cierre-con-excepcion" ? "Cierre con excepción" : "Decisión"}</b>{" "}
            · {formatFecha(d.fecha)} · {d.usuario}
            <p>{d.texto}</p>
            {d.evidencia && <p className="text-ink-secondary">Evidencia: {d.evidencia}</p>}
          </li>
        ))}
      </ul>
      <SoloLectura>
        {!abierta ? (
          <button type="button" onClick={() => setAbierta(true)} className="rounded border border-line px-2 py-0.5">Registrar una decisión</button>
        ) : (
          <div className="space-y-2">
            <label className="block">
              Tipo{" "}
              <select value={tipo} onChange={(e) => setTipo(e.target.value as typeof tipo)} className="rounded border border-line px-1 py-0.5">
                <option value="otro">Otra decisión</option>
                <option value="descartar-access">Descartar el Access para esta cuenta</option>
                <option value="cierre-con-excepcion">Cierre con excepción</option>
              </select>
            </label>
            <label className="block">Qué decidiste <input value={texto} onChange={(e) => setTexto(e.target.value)} maxLength={500} className="w-full rounded border border-line px-1 py-0.5" /></label>
            {tipo === "descartar-access" && (
              <label className="block">Evidencia y análisis que lo respalda <input value={evidencia} onChange={(e) => setEvidencia(e.target.value)} maxLength={500} className="w-full rounded border border-line px-1 py-0.5" /></label>
            )}
            {error && <p role="alert" className="text-status-danger">{error}</p>}
            <div className="flex gap-2">
              <button type="button" disabled={alta.isPending} onClick={() => alta.mutate()} className="rounded bg-finance px-3 py-1 text-white">Guardar decisión</button>
              <button type="button" onClick={() => setAbierta(false)} className="rounded border border-line px-2 py-0.5">Cancelar</button>
            </div>
          </div>
        )}
      </SoloLectura>
    </div>
  );
}

/**
 * Ficha de la cuenta (036): en qué etapa está, qué criterios cumple, y las acciones para cerrarla al corte.
 * Cerrar exige los 7 criterios; si falta alguno se cierra con excepción y su motivo. Solo Sergio aprueba.
 */
export function FichaCuenta({ idContacto }: { idContacto: number }) {
  const qc = useQueryClient();
  const { data: f, isLoading, error } = useQuery({ queryKey: ["revision-ficha", idContacto], queryFn: () => revisionCuentasApi.ficha(idContacto) });
  const [accion, setAccion] = useState<null | "cerrar" | "excepcion" | "sergio" | "evidencia">(null);
  const [motivo, setMotivo] = useState("");
  const [pregunta, setPregunta] = useState("");
  const [nota, setNota] = useState("");
  const [fallo, setFallo] = useState<string | null>(null);
  const refrescar = () => {
    for (const k of ["revision-ficha", "revision-pagos-sin-factura", "revision-tablero", "revision-cola"]) qc.invalidateQueries({ queryKey: [k] });
  };
  const cambiar = useMutation({
    mutationFn: (estado: "cerrada" | "cerrada-con-excepcion" | "esperando-sergio" | "esperando-evidencia" | "en-proceso") =>
      revisionCuentasApi.cambiarFicha(idContacto, {
        estado,
        nota: nota.trim() || null,
        motivoExcepcion: estado === "cerrada-con-excepcion" ? motivo.trim() : null,
        pregunta: estado === "esperando-sergio" ? pregunta.trim() : null,
      }),
    onSuccess: () => { setAccion(null); setFallo(null); refrescar(); },
    onError: (e) => setFallo(e instanceof Error ? e.message : "No se pudo guardar."),
  });

  if (isLoading) return <p className="text-xs text-ink-secondary">Calculando la ficha de la cuenta…</p>;
  if (error || !f || !Array.isArray(f.criterios)) return <p role="alert" className="text-xs text-status-danger">No se pudo calcular la ficha de la cuenta.</p>;

  const cerrada = f.estado === "cerrada" || f.estado === "cerrada-con-excepcion";
  const faltan = f.criterios.filter((c) => c.cumple === false);

  return (
    <section className="space-y-3 rounded border border-line p-3 text-xs">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h2 className="text-sm font-semibold">Ficha de la cuenta</h2>
        <span>Corte: <b>{formatFecha(f.corte)}</b></span>
        <span>Saldo al corte: <b>{formatMoneda(f.saldoAlCorte)}</b></span>
        <span className="rounded bg-surface-muted px-1.5">{NOMBRE_ESTADO[f.estadoEfectivo]}</span>
        <span>Cola {f.cola}: {NOMBRE_COLA[f.cola]}</span>
      </div>
      {f.otrosProblemas.length > 0 && (
        <p className="text-ink-secondary">Otros problemas: {f.otrosProblemas.map((c) => `${c} (${NOMBRE_COLA[c as Cola] ?? c})`).join(", ")}</p>
      )}
      {f.estadoEfectivo === "reabierta" && (
        <p role="alert" className="text-status-warning">El saldo al corte del cierre cambió: hay que revisar la cuenta de nuevo.</p>
      )}
      {f.antecedente035 && (
        <p className="text-ink-secondary">Antecedente: se marcó &quot;{f.antecedente035.estado}&quot; en la auditoría anterior{f.antecedente035.nota ? `: ${f.antecedente035.nota}` : ""}. No se toma como cerrada.</p>
      )}
      {f.fifoAplicadoAntes && <p className="text-ink-secondary">FIFO aplicado antes del método: las imputaciones se recalcularon antes de revisar los documentos.</p>}

      <ol className="flex flex-wrap gap-1" aria-label="Etapas">
        {ETAPAS.map((e) => (
          <li key={e.codigo} className={`rounded border px-2 py-0.5 ${e.codigo === f.etapa ? "border-finance bg-finance text-white" : "border-line"}`}>
            {e.codigo} {e.nombre}
          </li>
        ))}
      </ol>

      <ul className="space-y-1">
        {f.criterios.map((c) => (
          <li key={c.codigo} className="rounded border border-line p-2">
            <div className="flex flex-wrap items-baseline gap-2">
              <b>{c.codigo}</b> <EstadoCriterio c={c} /> <span>{c.texto}</span>
            </div>
            <p className="text-ink-secondary">{c.medido}{c.evidencia ? ` · evidencia: ${c.evidencia}` : ""}</p>
          </li>
        ))}
      </ul>

      {(f.moneda === "Dolares" || f.cola === "F") && <DiferenciaDeCambio idContacto={idContacto} />}

      <div className="rounded border border-line p-2">
        <p className="mb-1 font-medium">Qué evidencia manda</p>
        <p className="text-ink-secondary">Primero el proveedor con documento; el banco para el pago y el proveedor para la factura; el Access solo como referencia.</p>
      </div>

      {f.etapa === "E0" && (
        <SoloLectura>
          <Inventario idContacto={idContacto} alGuardar={refrescar} />
        </SoloLectura>
      )}

      {cerrada && f.cierre && (
        <p className="text-status-success">
          Cerrada al corte del {formatFecha(f.cierre.corte)} con saldo {formatMoneda(f.cierre.saldoAlCierre)}
          {f.cierre.conExcepcion ? ` (con excepción: ${f.cierre.motivoExcepcion ?? ""})` : ""} · {f.cierre.usuario}
        </p>
      )}
      {f.pregunta && <p className="text-status-warning">Pregunta para Sergio: {f.pregunta}</p>}

      <SoloLectura>
        <div className="space-y-2">
          <label className="block">
            Nota <input value={nota} onChange={(e) => setNota(e.target.value)} maxLength={500} className="w-full rounded border border-line px-1 py-0.5" />
          </label>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={() => setAccion("cerrar")} disabled={faltan.length > 0} title={faltan.length ? "Faltan criterios por cumplir" : undefined} className="rounded bg-finance px-3 py-1 text-white disabled:opacity-40">
              Cerrar al corte
            </button>
            <button type="button" onClick={() => setAccion("excepcion")} className="rounded border border-line px-3 py-1">Cerrar con excepción</button>
            <button type="button" onClick={() => setAccion("evidencia")} className="rounded border border-line px-3 py-1">Esperando evidencia</button>
            <button type="button" onClick={() => setAccion("sergio")} className="rounded border border-line px-3 py-1">Dejar una pregunta para Sergio</button>
            <button type="button" disabled={cambiar.isPending} onClick={() => cambiar.mutate("en-proceso")} className="rounded border border-line px-3 py-1">Marcar en proceso</button>
          </div>
          {accion === "cerrar" && (
            <p>
              ¿Cerrar la cuenta al corte del {formatFecha(f.corte)} con saldo {formatMoneda(f.saldoAlCorte)}?{" "}
              <button type="button" disabled={cambiar.isPending} onClick={() => cambiar.mutate("cerrada")} className="rounded bg-finance px-3 py-1 text-white">Sí, cerrar</button>{" "}
              <button type="button" onClick={() => setAccion(null)} className="rounded border border-line px-2 py-0.5">No</button>
            </p>
          )}
          {accion === "excepcion" && (
            <div className="space-y-1">
              <p>Faltan {faltan.length} criterios: {faltan.map((c) => c.codigo).join(", ") || "ninguno"}. Anotá por qué la cerrás igual:</p>
              <input value={motivo} onChange={(e) => setMotivo(e.target.value)} maxLength={500} className="w-full rounded border border-line px-1 py-0.5" aria-label="Motivo de la excepción" />
              <button type="button" disabled={cambiar.isPending || !motivo.trim()} onClick={() => cambiar.mutate("cerrada-con-excepcion")} className="rounded bg-finance px-3 py-1 text-white disabled:opacity-40">Cerrar con excepción</button>
            </div>
          )}
          {accion === "evidencia" && (
            <p>
              ¿Dejar la cuenta esperando evidencia?{" "}
              <button type="button" disabled={cambiar.isPending} onClick={() => cambiar.mutate("esperando-evidencia")} className="rounded border border-line px-3 py-1">Sí</button>
            </p>
          )}
          {accion === "sergio" && (
            <div className="space-y-1">
              <p>Qué hay que preguntarle a Sergio:</p>
              <input value={pregunta} onChange={(e) => setPregunta(e.target.value)} maxLength={300} className="w-full rounded border border-line px-1 py-0.5" aria-label="Pregunta para Sergio" />
              <button type="button" disabled={cambiar.isPending || !pregunta.trim()} onClick={() => cambiar.mutate("esperando-sergio")} className="rounded border border-line px-3 py-1 disabled:opacity-40">Guardar la pregunta</button>
            </div>
          )}
          {fallo && <p role="alert" className="text-status-danger">{fallo}</p>}
        </div>
      </SoloLectura>

      <Decisiones idContacto={idContacto} />

      {f.historial.length > 0 && (
        <details>
          <summary className="cursor-pointer">Historial de la ficha ({f.historial.length})</summary>
          <ul className="mt-1 space-y-0.5">
            {f.historial.map((h, i) => (
              <li key={`${h.fecha}-${i}`} className="text-ink-secondary">{formatFecha(h.fecha)} · {h.usuario} · {h.accion}</li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
