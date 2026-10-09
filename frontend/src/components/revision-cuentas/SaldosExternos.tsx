"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { formatFecha, formatMoneda, parseNumeroLocal } from "@/lib/format";
import { revisionCuentasApi, type FuenteSaldoExterno, type Moneda, type SaldoExterno } from "@/services/revisionCuentasApi";

const NOMBRE_FUENTE: Record<FuenteSaldoExterno, string> = {
  portal: "Portal del proveedor",
  pdf: "PDF o comprobante",
  mail: "Mail del proveedor",
  banco: "Banco",
  tarjeta: "Tarjeta",
  "sin-estado": "No se pide estado de cuenta",
};

const NOMBRE_CLASIFICACION: Record<SaldoExterno["clasificacion"], string> = {
  cierra: "Cierra",
  "menor-al-umbral": "Diferencia menor al umbral (se da por cerrada)",
  "con-diferencia": "Con diferencia: hay que explicarla",
};

/**
 * Saldos que informan el proveedor, el banco o la tarjeta, comparados con el saldo de la cuenta a esa fecha. Los carga una persona con su
 * fecha y su fuente: el sistema no entra a ningún portal. Elegís si le debemos al proveedor o si nos debe, y el sistema guarda el signo (positivo = a favor nuestro).
 */
export function SaldosExternos({ idContacto }: { idContacto: number }) {
  const qc = useQueryClient();
  const { data: respuesta } = useQuery({ queryKey: ["revision-saldos-externos", idContacto], queryFn: () => revisionCuentasApi.saldosExternos(idContacto) });
  const data = Array.isArray(respuesta) ? respuesta : [];
  const [abierto, setAbierto] = useState(false);
  const [fecha, setFecha] = useState("");
  const [saldo, setSaldo] = useState("");
  const [sentido, setSentido] = useState<"le-debemos" | "nos-debe">("le-debemos");
  const [moneda, setMoneda] = useState<Moneda>("Pesos");
  const [fuente, setFuente] = useState<FuenteSaldoExterno>("portal");
  const [referencia, setReferencia] = useState("");
  const [nota, setNota] = useState("");
  const [error, setError] = useState<string | null>(null);
  const refrescar = () => {
    for (const k of ["revision-saldos-externos", "revision-ficha", "revision-tablero", "revision-cola"]) qc.invalidateQueries({ queryKey: [k] });
  };
  const cargar = useMutation({
    mutationFn: () =>
      revisionCuentasApi.cargarSaldoExterno(idContacto, {
        fechaSaldo: fecha,
        // el importe se carga sin signo y el sentido lo da el selector: así no se invierte por error (positivo = a favor nuestro)
        saldo: fuente === "sin-estado" ? 0 : (sentido === "nos-debe" ? 1 : -1) * Math.abs(parseNumeroLocal(saldo)),
        moneda,
        fuente,
        referencia: referencia.trim() || null,
        nota: nota.trim() || null,
      }),
    onSuccess: () => { setAbierto(false); setSaldo(""); setReferencia(""); setNota(""); setError(null); refrescar(); },
    onError: (e) => setError(e instanceof Error ? e.message : "No se pudo guardar el saldo."),
  });
  const anular = useMutation({
    mutationFn: (id: number) => revisionCuentasApi.anularSaldoExterno(idContacto, id),
    onSuccess: refrescar,
    onError: (e) => setError(e instanceof Error ? e.message : "No se pudo anular el saldo."),
  });

  return (
    <section className="rounded border border-line p-3 text-xs">
      <h2 className="text-sm font-semibold">Saldo del proveedor, el banco o la tarjeta</h2>
      <p className="text-ink-secondary">Se compara con el saldo de la cuenta a esa fecha. Gana el proveedor con documento.</p>
      {data.length === 0 && <p className="mt-1 text-ink-secondary">Todavía no hay saldos externos cargados.</p>}
      <ul className="mt-1 space-y-1">
        {data.map((s) => (
          <li key={s.idSaldoExterno} className="rounded border border-line p-2">
            <div className="flex flex-wrap items-baseline gap-x-3">
              <b>{formatFecha(s.fechaSaldo)}</b>
              <span>{NOMBRE_FUENTE[s.fuente]}</span>
              {s.fuente !== "sin-estado" && <span>Saldo externo: <b>{formatMoneda(s.saldo, s.moneda)}</b></span>}
              {s.fuente !== "sin-estado" && <span>Saldo de la cuenta: <b>{formatMoneda(s.saldoCuentaALaFecha, s.moneda)}</b></span>}
              {s.fuente !== "sin-estado" && <span>Diferencia: <b>{formatMoneda(s.diferencia, s.moneda)}</b></span>}
              <span className={s.clasificacion === "con-diferencia" ? "text-status-danger" : "text-status-success"}>{NOMBRE_CLASIFICACION[s.clasificacion]}</span>
            </div>
            {s.referencia && <p className="text-ink-secondary">Referencia: {s.referencia}</p>}
            {s.nota && <p className="text-ink-secondary">Nota: {s.nota}</p>}
            <SoloLectura>
              <button type="button" disabled={anular.isPending} onClick={() => anular.mutate(s.idSaldoExterno)} className="mt-1 rounded border border-line px-2 py-0.5">Anular</button>
            </SoloLectura>
          </li>
        ))}
      </ul>
      {error && <p role="alert" className="mt-1 text-status-danger">{error}</p>}
      <SoloLectura>
        {!abierto ? (
          <button type="button" onClick={() => setAbierto(true)} className="mt-2 rounded border border-line px-3 py-1">Cargar un saldo</button>
        ) : (
          <div className="mt-2 space-y-2">
            <label className="block">
              De dónde sale{" "}
              <select value={fuente} onChange={(e) => setFuente(e.target.value as FuenteSaldoExterno)} className="rounded border border-line px-1 py-0.5">
                {(Object.keys(NOMBRE_FUENTE) as FuenteSaldoExterno[]).map((f) => <option key={f} value={f}>{NOMBRE_FUENTE[f]}</option>)}
              </select>
            </label>
            <label className="block">
              Fecha del saldo <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} className="rounded border border-line px-1 py-0.5" />
            </label>
            {fuente !== "sin-estado" && (
              <>
                <label className="block">
                  Qué informa el proveedor{" "}
                  <select value={sentido} onChange={(e) => setSentido(e.target.value as "le-debemos" | "nos-debe")} className="rounded border border-line px-1 py-0.5">
                    <option value="le-debemos">Le debemos nosotros (saldo en contra)</option>
                    <option value="nos-debe">Nos debe el proveedor (saldo a favor)</option>
                  </select>
                </label>
                <label className="block">
                  Importe, sin signo <input inputMode="decimal" value={saldo} onChange={(e) => setSaldo(e.target.value)} className="rounded border border-line px-1 py-0.5" />
                </label>
                <label className="block">
                  Moneda{" "}
                  <select value={moneda} onChange={(e) => setMoneda(e.target.value as Moneda)} className="rounded border border-line px-1 py-0.5">
                    <option value="Pesos">Pesos</option>
                    <option value="Dolares">Dólares</option>
                  </select>
                </label>
              </>
            )}
            <label className="block">
              Referencia (archivo o descripción) <input value={referencia} onChange={(e) => setReferencia(e.target.value)} maxLength={400} className="w-full rounded border border-line px-1 py-0.5" />
            </label>
            <label className="block">
              Nota{fuente === "sin-estado" ? " (obligatoria: por qué no se pide el estado de cuenta)" : ""}{" "}
              <input value={nota} onChange={(e) => setNota(e.target.value)} maxLength={500} className="w-full rounded border border-line px-1 py-0.5" />
            </label>
            <div className="flex gap-2">
              <button type="button" disabled={cargar.isPending || !fecha} onClick={() => cargar.mutate()} className="rounded bg-finance px-3 py-1 text-white disabled:opacity-40">
                {cargar.isPending ? "Guardando…" : "Guardar"}
              </button>
              <button type="button" onClick={() => setAbierto(false)} className="rounded border border-line px-2 py-0.5">Cancelar</button>
            </div>
          </div>
        )}
      </SoloLectura>
    </section>
  );
}
