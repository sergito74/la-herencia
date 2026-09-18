"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useState } from "react";

import {
  eliminarPagoResumen,
  fetchResumenDetalle,
  quitarVinculoCompra,
  registrarPagoResumen,
  vincularCompra,
  type LineaConsumo,
} from "@/services/tarjetasResumenesApi";
import { fetchPagosCandidatos } from "@/services/tarjetasApi";
import { fetchCompras } from "@/services/comprasApi";
import { urlDocumentoLocal } from "@/services/comprasApi";
import { urlParaAbrirDocumento } from "@/lib/documentoLocal";
import { formatMoneda } from "@/lib/format";
import { filterInputClass } from "@/components/ui/FilterBar";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { useToast } from "@/components/ui/Toast";

function Semaforo({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
      <span
        aria-hidden
        className={`inline-block h-2.5 w-2.5 shrink-0 rounded-full ${ok ? "bg-status-success" : "bg-status-danger"}`}
      />
      <span className={ok ? "text-status-success" : "text-status-danger"}>{label}</span>
    </span>
  );
}

const CARGOS: [string, string][] = [
  ["impuestoSellos", "Impuesto de Sellos"],
  ["gastosAdmin", "Gastos de Administración"],
  ["mantCuenta", "Mantenimiento de Cuenta"],
  ["renovAnual", "Renovación Anual"],
  ["promocionBNA", "Promoción BNA"],
  ["creditoContingente", "Crédito Contingente"],
  ["intFinanc", "Interés de Financiación"],
  ["intCompens", "Interés Compensatorio"],
  ["iva105", "IVA 10,5%"],
  ["percepIVA105", "Percepción IVA 10,5%"],
  ["iva21", "IVA 21%"],
  ["percepIVA21", "Percepción IVA 21%"],
  ["percepIIBB", "Percepción IIBB"],
  ["ajusteResAnterior", "Ajuste de Resumen Anterior"],
];

function VincularCompraForm({
  idLineaConsumo,
  importeSugerido,
  nroDocumentoSugerido,
  onLinked,
}: {
  idLineaConsumo: number;
  importeSugerido: number;
  nroDocumentoSugerido?: string | null;
  onLinked: () => void;
}) {
  // El 96% de las líneas de consumo ya vienen con proveedor/documento
  // reales del resumen del banco — la mayoría se auto-vincula sola
  // (ver auto_vincular_compras en el backend). Este buscador solo hace
  // falta para el resto: precarga la búsqueda con el número de
  // documento que la línea ya trae (aunque no haya matcheado exacto,
  // suele acercar el resultado) y el importe con el de la línea, para
  // que en el caso común alcance con elegir de la lista y confirmar.
  const [busqueda, setBusqueda] = useState(nroDocumentoSugerido ?? "");
  const [importeImputado, setImporteImputado] = useState(importeSugerido);
  const [resultados, setResultados] = useState<{ idCompra: number; label: string }[]>([]);
  const [idCompra, setIdCompra] = useState<number | null>(null);
  const [buscando, setBuscando] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const { showToast } = useToast();

  async function buscar() {
    if (!busqueda.trim()) return;
    setBuscando(true);
    try {
      const [porDocumento, porProveedor] = await Promise.all([
        fetchCompras({ numeroDocumento: busqueda, page: 1, pageSize: 10 }),
        fetchCompras({ proveedor: busqueda, page: 1, pageSize: 10 }),
      ]);
      const vistos = new Set<number>();
      const items = [...porDocumento.items, ...porProveedor.items].filter((c) =>
        vistos.has(c.idCompra) ? false : (vistos.add(c.idCompra), true)
      );
      setResultados(
        items.map((c) => ({
          idCompra: c.idCompra,
          label: `${c.proveedor?.razonSocial ?? "—"} · ${c.tipoDocumento ?? ""} ${c.numeroDocumento ?? ""} (${c.fecha ?? "—"}) — ${
            c.importeDocumento != null ? formatMoneda(c.importeDocumento) : "importe desconocido"
          }`,
        }))
      );
    } finally {
      setBuscando(false);
    }
  }

  useEffect(() => {
    if (nroDocumentoSugerido) buscar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function vincular() {
    if (idCompra == null) return;
    setGuardando(true);
    try {
      await vincularCompra(idLineaConsumo, idCompra, importeImputado);
      showToast("Factura vinculada.", "success");
      onLinked();
    } catch {
      showToast("No se pudo vincular la factura.", "danger");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div className="mt-1 flex flex-wrap items-center gap-1 rounded-sm border border-dashed border-border p-1">
      <input
        className={`${filterInputClass} min-w-[10rem] flex-1 px-1.5 py-0.5 text-xs`}
        placeholder="Buscar proveedor…"
        value={busqueda}
        onChange={(e) => setBusqueda(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), buscar())}
      />
      <button
        type="button"
        onClick={buscar}
        disabled={buscando}
        className="rounded-sm border border-border px-2 py-0.5 text-xs text-ink-secondary hover:text-ink-primary"
      >
        {buscando ? "Buscando…" : "Buscar"}
      </button>
      {resultados.length > 0 && (
        <select
          className={`${filterInputClass} min-w-[14rem] px-1.5 py-0.5 text-xs`}
          value={idCompra ?? ""}
          onChange={(e) => setIdCompra(e.target.value ? Number(e.target.value) : null)}
        >
          <option value="">Elegir compra…</option>
          {resultados.map((r) => (
            <option key={r.idCompra} value={r.idCompra}>
              {r.label}
            </option>
          ))}
        </select>
      )}
      <input
        type="number"
        className={`${filterInputClass} w-24 px-1.5 py-0.5 text-right text-xs font-data`}
        placeholder="Importe"
        value={importeImputado || ""}
        onChange={(e) => setImporteImputado(Number(e.target.value) || 0)}
      />
      <button
        type="button"
        onClick={vincular}
        disabled={idCompra == null || guardando}
        className="rounded-sm bg-finance px-2 py-0.5 text-xs text-white hover:opacity-90 disabled:opacity-40"
      >
        {guardando ? "Vinculando…" : "Vincular"}
      </button>
    </div>
  );
}

function LineaConsumoRow({ linea, onChanged }: { linea: LineaConsumo; onChanged: () => void }) {
  const [mostrarBuscador, setMostrarBuscador] = useState(false);
  const { showToast } = useToast();

  async function quitar(idVinculo: number) {
    if (linea.idLineaConsumo == null) return;
    try {
      await quitarVinculoCompra(linea.idLineaConsumo, idVinculo);
      onChanged();
    } catch {
      showToast("No se pudo quitar el vínculo.", "danger");
    }
  }

  return (
    <>
      <tr className="border-t border-border align-top">
        <td className="py-1">{linea.fechaCompra}</td>
        <td className="py-1">{linea.detalle}</td>
        <td className="py-1 text-right font-data">{formatMoneda(linea.importe)}</td>
        <td className="py-1">
          <Semaforo
            ok={linea.comprasVinculadas.length > 0}
            label={linea.comprasVinculadas.length === 0 ? "Sin vincular" : "Vinculada"}
          />
          {linea.comprasVinculadas.map((v) => (
            <div key={v.idVinculo} className="flex items-center gap-1">
              <span>
                {v.proveedor ?? "—"} · {v.tipoDocumento ?? ""} {v.numeroDocumento ?? ""} —{" "}
                {formatMoneda(v.importeImputado)}
              </span>
              <button
                type="button"
                onClick={() => quitar(v.idVinculo)}
                className="text-ink-secondary hover:text-status-danger"
                title="Quitar vínculo"
              >
                ✕
              </button>
            </div>
          ))}
          {linea.comprasVinculadas.length === 0 && (
            <button
              type="button"
              onClick={() => setMostrarBuscador((v) => !v)}
              className="mt-0.5 text-finance underline"
            >
              + Vincular factura
            </button>
          )}
          {mostrarBuscador && linea.comprasVinculadas.length === 0 && linea.idLineaConsumo != null && (
            <VincularCompraForm
              idLineaConsumo={linea.idLineaConsumo}
              importeSugerido={linea.importe}
              nroDocumentoSugerido={linea.nroDocumento}
              onLinked={() => {
                setMostrarBuscador(false);
                onChanged();
              }}
            />
          )}
        </td>
      </tr>
    </>
  );
}

export default function ResumenDetallePage() {
  const params = useParams<{ idResumen: string }>();
  const idResumen = Number(params.idResumen);
  const router = useRouter();
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["tarjeta-resumen-detalle", idResumen],
    queryFn: () => fetchResumenDetalle(idResumen),
  });

  const { data: candidatos } = useQuery({
    queryKey: ["tarjeta-pagos-candidatos", data?.idTarjeta],
    queryFn: () => fetchPagosCandidatos(data!.idTarjeta),
    enabled: data != null,
  });

  function invalidar() {
    refetch();
    if (data) {
      queryClient.invalidateQueries({ queryKey: ["tarjeta-movimientos", data.idTarjeta] });
      queryClient.invalidateQueries({ queryKey: ["tarjeta-pagos-candidatos", data.idTarjeta] });
    }
  }

  async function vincularPago(candidato: { origen: string; idMovimiento: number; fecha: string; importe: number }) {
    try {
      await registrarPagoResumen(idResumen, {
        fecha: candidato.fecha,
        importe: candidato.importe,
        origen: candidato.origen,
        idMovimientoOrigen: candidato.idMovimiento,
      });
      showToast("Pago vinculado.", "success");
      invalidar();
    } catch {
      showToast("No se pudo vincular el pago.", "danger");
    }
  }

  async function eliminarPago(idPago: number) {
    try {
      await eliminarPagoResumen(idResumen, idPago);
      invalidar();
    } catch {
      showToast("No se pudo eliminar el pago.", "danger");
    }
  }

  const totalPagado = data?.pagos.reduce((acc, p) => acc + p.importe, 0) ?? 0;
  const conciliado = data != null && totalPagado >= data.totalCalculado - 0.02;

  return (
    <main className="mx-auto max-w-none px-8 py-3">
      <button type="button" onClick={() => router.back()} className="text-sm text-finance underline">
        ← Volver
      </button>

      {isLoading && <LoadingState />}
      {isError && <ErrorState message="Ocurrió un error al cargar el resumen." onRetry={() => refetch()} />}

      {data && (
        <div className="mt-2 space-y-3">
          <div className="flex items-center justify-between">
            <h1 className="text-base font-semibold">
              Resumen {data.codigo} — {data.tarjeta}
            </h1>
            <div className="flex items-center gap-3">
              <Semaforo ok={conciliado} label={conciliado ? "Pago conciliado" : "Falta conciliar el pago"} />
              <Link href={`/finanzas/tarjetas/resumenes/${idResumen}/editar`} className="text-sm text-finance underline">
                Editar
              </Link>
            </div>
          </div>
          <p className="text-xs text-ink-secondary">
            Cierre: {data.fechaCierre} · Vencimiento: {data.fechaVencimiento}
          </p>
          {data.urlResumenOriginal && (
            <p className="text-xs">
              <a
                href={urlParaAbrirDocumento(data.urlResumenOriginal, "", urlDocumentoLocal)}
                target="_blank"
                rel="noreferrer"
                className="text-finance underline"
              >
                Ver resumen original (PDF)
              </a>
            </p>
          )}

          <div className="rounded-md border border-border bg-surface p-2">
            <h2 className="text-xs font-medium text-ink-secondary">Cargos e impuestos</h2>
            <dl className="mt-1 grid grid-cols-[repeat(auto-fit,minmax(11rem,1fr))] gap-x-4 gap-y-1 text-xs">
              {CARGOS.map(([key, label]) => {
                const value = (data as unknown as Record<string, number>)[key] ?? 0;
                if (!value) return null;
                return (
                  <div key={key} className="flex justify-between gap-2">
                    <dt className="text-ink-secondary">{label}</dt>
                    <dd className="font-data">{formatMoneda(value)}</dd>
                  </div>
                );
              })}
            </dl>
            <p className="mt-2 font-data text-sm font-semibold text-ink-primary">
              Total calculado: {formatMoneda(data.totalCalculado)}
            </p>
          </div>

          <div className="rounded-md border border-border bg-surface p-2">
            <h2 className="text-xs font-medium text-ink-secondary">
              Líneas de consumo {data.lineas.length === 0 && "(ninguna — solo cabecera)"}
            </h2>
            {data.lineas.length > 0 && (
              <table className="mt-1 w-full text-xs">
                <thead>
                  <tr className="text-left text-ink-secondary">
                    <th className="py-1">Fecha</th>
                    <th className="py-1">Detalle</th>
                    <th className="py-1 text-right">Importe</th>
                    <th className="py-1">Facturas vinculadas</th>
                  </tr>
                </thead>
                <tbody>
                  {data.lineas.map((l) => (
                    <LineaConsumoRow key={l.idLineaConsumo} linea={l} onChanged={invalidar} />
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="rounded-md border border-border bg-surface p-2">
            <h2 className="text-xs font-medium text-ink-secondary">Pagos registrados</h2>
            {data.pagos.length === 0 && <p className="mt-1 text-xs text-ink-secondary">Ningún pago registrado todavía.</p>}
            {data.pagos.length > 0 && (
              <table className="mt-1 w-full text-xs">
                <tbody>
                  {data.pagos.map((p) => (
                    <tr key={p.idPago} className="border-t border-border">
                      <td className="py-1">{p.fecha}</td>
                      <td className="py-1 text-right font-data">{formatMoneda(p.importe)}</td>
                      <td className="py-1 text-ink-secondary">{p.origen ?? "Manual"}</td>
                      <td className="py-1 text-right">
                        <button
                          type="button"
                          onClick={() => eliminarPago(p.idPago)}
                          className="text-ink-secondary hover:text-status-danger"
                        >
                          ✕
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {!conciliado && candidatos && candidatos.length > 0 && (
              <div className="mt-2">
                <h3 className="text-xs text-ink-secondary">
                  Movimientos bancarios candidatos (misma tarjeta, no vinculados todavía)
                </h3>
                <ul className="mt-1 space-y-1">
                  {candidatos.map((c) => (
                    <li key={`${c.origen}-${c.idMovimiento}`} className="flex items-center justify-between gap-2 text-xs">
                      <span>
                        {c.fecha} · {formatMoneda(c.importe)} · {c.concepto ?? c.origen}
                      </span>
                      <button
                        type="button"
                        onClick={() => vincularPago(c)}
                        className="rounded-sm border border-border px-2 py-0.5 text-ink-secondary hover:text-ink-primary"
                      >
                        Vincular como pago de este resumen
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </main>
  );
}
