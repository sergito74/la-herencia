"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { usePathname, useSearchParams } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/components/auth/AuthContext";
import { formatFecha, formatMoneda } from "@/lib/format";
import { urlDocumentoLocal } from "@/services/comprasApi";
import {
  ETIQUETA_MODULO, getNuevos, getResumenNuevos, type ResumenNuevos, marcarNuevoRevisado, moverNuevo, yaCargadoNuevo, type DocumentoNuevo, type ModuloAviso,
} from "@/services/documentosNuevosApi";

/** Dónde se carga a mano un documento de cada módulo. */
const CARGA_MANUAL: Partial<Record<ModuloAviso, { href: string; texto: string }>> = {
  pagos: { href: "/finanzas/ordenes-pago", texto: "Vincular recibo" },
  compras: { href: "/compras/nueva", texto: "Cargar compra" },
  impuestos: { href: "/finanzas/impuestos/nueva", texto: "Cargar impuesto" },
  ventas: { href: "/ventas/hacienda/nueva", texto: "Cargar venta de hacienda" },
  granos: { href: "/ventas/granos/nueva", texto: "Cargar venta de granos" },
  tesoreria: { href: "/finanzas/tesoreria", texto: "Ir a importar el resumen" },
};

/** El formulario de carga arranca con el PDF y los datos del aviso (24/11/2026: antes abría vacío). */
function hrefCarga(base: string, d: DocumentoNuevo): string {
  const p = new URLSearchParams();
  if (d.idContacto) p.set("idContacto", String(d.idContacto));
  if (d.contacto) p.set("proveedor", d.contacto);
  if (d.fecha) p.set("fecha", d.fecha.slice(0, 10));
  if (d.numero) p.set("numeroDocumento", d.numero);
  if (d.ruta) p.set("documentoOriginal", d.ruta);
  const q = p.toString();
  return q ? `${base}${base.includes("?") ? "&" : "?"}${q}` : base;
}

const DESTINOS: ModuloAviso[] = ["compras", "impuestos", "ventas", "granos", "tesoreria", "cuentas_corrientes", "pagos"];

function Detalle({ d, admin }: { d: DocumentoNuevo; admin: boolean }) {
  const qc = useQueryClient();
  const [destino, setDestino] = useState<ModuloAviso | "">("");
  const refrescar = () => qc.invalidateQueries({ queryKey: ["documentos-nuevos"] });
  const revisar = useMutation({ mutationFn: () => marcarNuevoRevisado(d.idDocumentoNuevo), onSuccess: refrescar });
  const yaCargado = useMutation({ mutationFn: () => yaCargadoNuevo(d.idDocumentoNuevo), onSuccess: refrescar });
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

      {d.estado === "cargado_solo" && d.motivo && (
        <p className="rounded-sm bg-status-success-bg px-2 py-1 text-xs text-status-success">Cargado solo. Revisar: {d.motivo}</p>
      )}
      {d.estado === "para_cargar" && (
        <p className="rounded-sm bg-status-warning-bg px-2 py-1 text-xs text-status-warning">
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
        {d.ruta && <a href={urlDocumentoLocal(d.ruta)} target="_blank" rel="noreferrer" className="text-finance hover:underline">
          Ver archivo ({d.archivo})
        </a>}
        {d.enlace && (
          <Link href={d.enlace} className="text-finance hover:underline">
            {d.estado === "cargado_solo" ? "Ver y corregir" : "Abrir"}
          </Link>
        )}
        {admin && d.estado === "para_cargar" && !d.idRegistro && carga && (
          <Link href={hrefCarga(carga.href, d)} className="text-finance hover:underline">{carga.texto}</Link>
        )}
        {admin && d.estado === "para_cargar" && !d.idRegistro && (
          <button type="button" disabled={yaCargado.isPending} onClick={() => yaCargado.mutate()}
            title="Ya está cargado: el aviso sale de la lista" className="text-finance hover:underline disabled:opacity-40">
            Ya está cargado
          </button>
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
            className="rounded-md bg-finance font-medium text-white shadow-sm transition-colors hover:bg-finance/90 disabled:opacity-60 ml-auto px-3 py-1 text-xs">
            Revisado
          </button>
        )}
      </div>
      {(revisar.isError || mover.isError || yaCargado.isError) && (
        <p className="text-sm text-status-danger">{(revisar.error ?? mover.error ?? yaCargado.error)?.message}</p>
      )}
    </div>
  );
}

function Lista({ modulo, titulo }: { modulo: ModuloAviso; titulo: string }) {
  const { usuario } = useAuth();
  const [abierto, setAbierto] = useState<number | null>(null);
  const q = useQuery({ queryKey: ["documentos-nuevos", "lista", modulo], queryFn: () => getNuevos(modulo) });
  const items = q.data?.items ?? [];
  if (q.isError) return <p className="text-sm text-status-danger">No se pudieron leer los documentos nuevos: {q.error.message}</p>;
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
const CLAVE_RESUMEN: Record<ModuloAviso, keyof ResumenNuevos> = {
  compras: "compras", impuestos: "impuestos", ventas: "ventas", granos: "granos", tesoreria: "tesoreria",
  cuentas_corrientes: "cuentasCorrientes", sin_clasificar: "sinClasificar", pagos: "pagos", ganaderia: "ganaderia",
};

/** 24/11/2026: franja visible en la pantalla del módulo cuando hay documentos nuevos sin revisar (antes solo se veían
 * entrando por el número azul del menú y quedaban escondidos). */
export function AvisoNuevosPendientes({ modulos }: { modulos: ModuloAviso[] }) {
  const pathname = usePathname();
  const q = useQuery({ queryKey: ["documentos-nuevos", "resumen"], queryFn: getResumenNuevos, staleTime: 60_000 });
  const n = q.data ? modulos.reduce((s, m) => s + Number(q.data[CLAVE_RESUMEN[m]] ?? 0), 0) : 0;
  if (!n) return null;
  return (
    <p className="mb-2 flex items-center gap-3 rounded-md border border-finance/40 bg-finance-light px-3 py-2 text-sm text-finance">
      Hay {n} {n === 1 ? "documento nuevo" : "documentos nuevos"} para revisar.
      <Link href={`${pathname}?nuevos=1`} className="font-medium underline">Revisar</Link>
    </p>
  );
}

export function NuevosParaRevisar({ modulo }: { modulo: ModuloAviso }) {
  const params = useSearchParams();
  if (params.get("nuevos") !== "1") return <AvisoNuevosPendientes modulos={[modulo]} />;

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
