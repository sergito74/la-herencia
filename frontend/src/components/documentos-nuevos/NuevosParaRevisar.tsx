"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/components/auth/AuthContext";
import { formatFecha, formatMoneda } from "@/lib/format";
import { urlDocumentoLocal } from "@/services/comprasApi";
import {
  ETIQUETA_MODULO, getNuevos, marcarNuevoRevisado, moverNuevo, type DocumentoNuevo, type ModuloAviso,
} from "@/services/documentosNuevosApi";

/** Dónde se carga a mano un documento de cada módulo. */
const CARGA_MANUAL: Partial<Record<ModuloAviso, { href: string; texto: string }>> = {
  pagos: { href: "/finanzas/ordenes-pago", texto: "Vincular recibo" },
  compras: { href: "/compras/nueva", texto: "Cargar compra" },
  impuestos: { href: "/finanzas/impuestos/nueva", texto: "Cargar impuesto" },
  ventas: { href: "/ventas/hacienda/nueva", texto: "Cargar venta" },
  tesoreria: { href: "/finanzas/tesoreria", texto: "Ir a importar el resumen" },
};

const DESTINOS: ModuloAviso[] = ["compras", "impuestos", "ventas", "tesoreria", "cuentas_corrientes", "pagos"];

function Detalle({ d, admin }: { d: DocumentoNuevo; admin: boolean }) {
  const qc = useQueryClient();
  const [destino, setDestino] = useState<ModuloAviso | "">("");
  const refrescar = () => qc.invalidateQueries({ queryKey: ["documentos-nuevos"] });
  const revisar = useMutation({ mutationFn: () => marcarNuevoRevisado(d.idDocumentoNuevo), onSuccess: refrescar });
  const mover = useMutation({
    mutationFn: (m: ModuloAviso) => moverNuevo(d.idDocumentoNuevo, m),
    onSuccess: refrescar,
  });
  const carga = CARGA_MANUAL[d.modulo];

  return (
    <div className="space-y-2 rounded-md border border-border p-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2 text-sm">
        <div>
          <strong>{d.contacto ?? "Emisor sin identificar"}</strong>
          <span className="ml-2 text-ink-secondary">
            {d.tipo} {d.numero ?? ""} {d.fecha ? `· ${formatFecha(d.fecha)}` : ""}
          </span>
          <div className="text-xs text-ink-muted">{d.origen} · {d.origenDetalle}</div>
        </div>
        <span className="font-medium">{d.total == null ? "—" : formatMoneda(d.total, "Pesos")}</span>
      </div>

      {d.estado === "para_cargar" && (
        <p className="rounded-sm bg-amber-50 px-2 py-1 text-xs text-amber-900">
          Para cargar a mano{d.motivo ? `: ${d.motivo}` : ""}
          {d.idRegistro ? " · ya se cargó; falta marcarlo como revisado" : ""}
        </p>
      )}

      {d.renglones && d.renglones.length > 0 && (
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border text-left text-ink-muted">
              <th className="py-1 pr-3">Detalle</th>
              <th className="py-1 pr-3">Rubro</th>
              <th className="py-1 pr-3">Centro de costo</th>
              <th className="py-1 pr-3 text-right">Importe</th>
              <th className="py-1 text-right">IVA</th>
            </tr>
          </thead>
          <tbody>
            {d.renglones.map((r, i) => (
              <tr key={i} className="border-b border-border/50">
                <td className="py-1 pr-3">{r.detalle}</td>
                <td className="py-1 pr-3">{r.rubro ?? "—"}</td>
                <td className="py-1 pr-3">{r.centroCosto ?? "—"}</td>
                <td className="py-1 pr-3 text-right whitespace-nowrap">
                  {r.importe == null ? "—" : formatMoneda(r.importe, "Pesos")}
                </td>
                <td className="py-1 text-right">{r.iva ? `${String(r.iva).replace(".", ",")}%` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div className="flex flex-wrap items-center gap-3 text-sm">
        <a href={urlDocumentoLocal(d.ruta)} target="_blank" rel="noreferrer" className="text-finance hover:underline">
          Ver archivo ({d.archivo})
        </a>
        {d.enlace && (
          <Link href={d.enlace} className="text-finance hover:underline">
            {d.estado === "cargado_solo" ? "Ver y corregir" : "Abrir"}
          </Link>
        )}
        {admin && d.estado === "para_cargar" && !d.idRegistro && carga && (
          <Link href={carga.href} className="text-finance hover:underline">{carga.texto}</Link>
        )}
        {admin && d.modulo === "sin_clasificar" && (
          <span className="flex items-center gap-1">
            <select value={destino} onChange={(e) => setDestino(e.target.value as ModuloAviso | "")}
              className="rounded-sm border border-border px-1 py-0.5 text-xs">
              <option value="">¿A qué módulo va?</option>
              {DESTINOS.map((m) => <option key={m} value={m}>{ETIQUETA_MODULO[m]}</option>)}
            </select>
            <button type="button" disabled={!destino || mover.isPending} onClick={() => destino && mover.mutate(destino)}
              className="rounded-md border border-border px-2 py-0.5 text-xs disabled:opacity-40">
              Mover
            </button>
          </span>
        )}
        {admin && (
          <button type="button" disabled={revisar.isPending} onClick={() => revisar.mutate()}
            className="ml-auto rounded-md bg-finance px-3 py-1 text-xs font-medium text-white disabled:opacity-40">
            Revisado
          </button>
        )}
      </div>
      {(revisar.isError || mover.isError) && (
        <p className="text-sm text-red-700">{(revisar.error ?? mover.error)?.message}</p>
      )}
    </div>
  );
}

function Lista({ modulo, titulo }: { modulo: ModuloAviso; titulo: string }) {
  const { usuario } = useAuth();
  const [abierto, setAbierto] = useState<number | null>(null);
  const q = useQuery({ queryKey: ["documentos-nuevos", "lista", modulo], queryFn: () => getNuevos(modulo) });
  const items = q.data?.items ?? [];
  if (q.isError) return <p className="text-sm text-red-700">No se pudieron leer los documentos nuevos: {q.error.message}</p>;
  if (items.length === 0) return null;
  const actual = items.find((d) => d.idDocumentoNuevo === abierto) ?? items[0];

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold">{titulo} ({q.data?.total ?? items.length})</h3>
      <div className="flex flex-wrap gap-1">
        {items.map((d) => (
          <button key={d.idDocumentoNuevo} type="button" onClick={() => setAbierto(d.idDocumentoNuevo)}
            className={`rounded-sm border px-2 py-0.5 text-xs ${d.idDocumentoNuevo === actual.idDocumentoNuevo
              ? "border-finance bg-finance-light text-finance" : "border-border text-ink-secondary"}`}>
            {d.contacto ?? d.archivo} {d.fecha ? formatFecha(d.fecha) : ""}
            {d.estado === "para_cargar" ? " · a mano" : ""}
          </button>
        ))}
      </div>
      <Detalle key={actual.idDocumentoNuevo} d={actual} admin={usuario?.rol === "Administrador"} />
    </div>
  );
}

/** Vista "Nuevos para revisar" de un módulo (043, US1). Se muestra al entrar con `?nuevos=1` (desde el número
 * del menú): lo que el sistema incorporó solo, con el primero abierto. Compras usa `RevisionComprasEnFormulario`. */
export function NuevosParaRevisar({ modulo }: { modulo: ModuloAviso }) {
  const params = useSearchParams();
  if (params.get("nuevos") !== "1") return null;

  return (
    <section className="space-y-4 rounded-md border border-finance/40 bg-surface p-3">
      <div>
        <h2 className="text-base font-semibold">Nuevos para revisar</h2>
        <p className="text-xs text-ink-secondary">
          Documentos que llegaron solos (portales y mails). Revisá contacto, imputación e importes; si algo está mal,
          corregilo; cuando esté bien, marcalo como revisado.
        </p>
      </div>
      <Lista modulo={modulo} titulo={ETIQUETA_MODULO[modulo]} />

    </section>
  );
}
