"use client";

import { useEffect, useState } from "react";

import { API_BASE_URL, ApiError, apiGet, apiPost } from "@/services/apiClient";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { FilterBar, FilterField, FilterSubmitButton, filterInputClass } from "@/components/ui/FilterBar";
import { SoloLectura } from "@/components/auth/SoloLectura";
import { useToast } from "@/components/ui/Toast";
import { ResumenImputacion } from "@/components/imputacion/ResumenImputacion";

interface Fraccion {
  idPropuesta: number;
  idCorrida: string;
  origen: "Insumo" | "Contratista";
  idLote: number | null;
  lote: string | null;
  idCultivo: number | null;
  cultivo: string | null;
  idCampania: number | null;
  campania: string | null;
  idCentroCosto: number | null;
  centroCosto: string | null;
  esGanaderia: boolean | null;
  importe: number;
  cantidad: number | null;
  unidad: string | null;
  idOrdenTrabajo: number | null;
  estado: "Pendiente" | "Aprobada" | "RequiereIntervencion";
}

interface Linea {
  idDetalleCompra: number;
  producto: string;
  cantidad: number;
  unidad: string | null;
  precioUnitario: number;
  campaniaManual: string | null;
  centroCostoManual: string | null;
  rubroManual: string | null;
  fracciones: Fraccion[];
  totalFracciones: number;
}

interface Documento {
  idCompra: number;
  fecha: string;
  idContacto: number | null;
  proveedor: string | null;
  tipoDocumento: string | null;
  numeroDocumento: string | null;
  moneda: string;
  lineas: Linea[];
  totalDocumento: number;
}

type Estado = "Pendiente" | "Aprobada" | "RequiereIntervencion";

function etiquetaDestino(f: Fraccion): string {
  if (f.estado === "RequiereIntervencion") return "Requiere intervención";
  if (f.cultivo) return `${f.cultivo} / ${f.campania ?? "—"}`;
  if (f.centroCosto) return f.centroCosto;
  if (f.esGanaderia) return "Ganadería";
  return "En stock sin consumir";
}

function badgeEstado(estado: Fraccion["estado"]) {
  const clases: Record<Fraccion["estado"], string> = {
    Aprobada: "bg-agro-light text-agro",
    Pendiente: "bg-finance-light text-finance",
    RequiereIntervencion: "bg-red-100 text-red-700",
  };
  return <span className={`rounded-full px-2 py-0.5 text-xs ${clases[estado]}`}>{estado}</span>;
}

function LineaRow({ linea, onAprobada }: { linea: Linea; onAprobada: (idCorrida: string) => void }) {
  const [abierta, setAbierta] = useState(false);
  const [aprobando, setAprobando] = useState<string | null>(null);
  const tiene = linea.fracciones.length > 0;
  const { showToast } = useToast();

  async function aprobar(idCorrida: string) {
    setAprobando(idCorrida);
    try {
      await apiPost(`/api/imputacion/propuestas/${idCorrida}/aprobar`, {});
      onAprobada(idCorrida);
      showToast("Propuesta aprobada.", "success");
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : "No se pudo aprobar la propuesta.", "danger");
    } finally {
      setAprobando(null);
    }
  }

  return (
    <>
      <tr className="border-t border-border text-sm">
        <td className="py-1.5 pl-6">
          {tiene && (
            <button
              type="button"
              onClick={() => setAbierta((v) => !v)}
              className="mr-2 inline-flex h-5 w-5 items-center justify-center rounded border border-border text-xs text-ink-secondary"
              aria-label={abierta ? "Contraer" : "Desplegar"}
            >
              {abierta ? "−" : "+"}
            </button>
          )}
          {linea.producto}
        </td>
        <td className="py-1.5">{linea.cantidad?.toLocaleString("es-AR")} {linea.unidad}</td>
        <td className="py-1.5">{linea.campaniaManual ?? "—"}</td>
        <td className="py-1.5">{linea.centroCostoManual ?? linea.rubroManual ?? "—"}</td>
        <td className="py-1.5 text-ink-secondary">
          {tiene ? (
            <>
              {linea.totalFracciones.toLocaleString("es-AR")} ({linea.fracciones.length} fracción
              {linea.fracciones.length > 1 ? "es" : ""})
            </>
          ) : (
            "sin propuesta"
          )}
        </td>
      </tr>
      {abierta &&
        linea.fracciones.map((f) => (
          <tr key={f.idPropuesta} className="border-t border-border bg-surface-sunken text-xs">
            <td className="py-1 pl-14 text-ink-secondary">↳ {etiquetaDestino(f)}</td>
            <td className="py-1">{f.origen === "Contratista" ? "No aplica" : f.cantidad == null ? "No registrada" : `${f.cantidad.toLocaleString("es-AR", { maximumFractionDigits: 4 })} ${f.unidad || "(unidad no informada)"}`}</td>
            <td className="py-1">{f.campania ?? "—"}</td>
            <td className="py-1">{f.lote ? `Lote ${f.lote}` : f.origen}</td>
            <td className="py-1">
              <span className="mr-2">{f.importe.toLocaleString("es-AR")} ARS</span>
              {badgeEstado(f.estado)}
              {f.estado === "Pendiente" && (
                <SoloLectura>
                  <button
                    type="button"
                    onClick={() => aprobar(f.idCorrida)}
                    disabled={aprobando === f.idCorrida}
                    className="ml-2 rounded border border-agro px-1.5 py-0.5 text-xs text-agro disabled:opacity-60"
                  >
                    {aprobando === f.idCorrida ? "Aprobando…" : "Aprobar"}
                  </button>
                </SoloLectura>
              )}
              {f.estado !== "Aprobada" && (
                <a
                  href={`/imputacion?idDetalleCompra=${linea.idDetalleCompra}`}
                  className="ml-2 text-ink-secondary underline"
                >
                  Revisar
                </a>
              )}
            </td>
          </tr>
        ))}
    </>
  );
}

export default function DocumentosImputacionPage() {
  const [documentos, setDocumentos] = useState<Documento[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const [totalGeneral, setTotalGeneral] = useState(0);

  const [idContacto, setIdContacto] = useState<number | null>(null);
  const [proveedorNombre, setProveedorNombre] = useState<string | null>(null);
  const [fechaDesde, setFechaDesde] = useState("");
  const [fechaHasta, setFechaHasta] = useState("");
  const [estado, setEstado] = useState<Estado | "">("");
  const [filtrosAplicados, setFiltrosAplicados] = useState<{ idContacto: number | null; fechaDesde: string; fechaHasta: string; estado: Estado | "" }>({
    idContacto: null,
    fechaDesde: "",
    fechaHasta: "",
    estado: "",
  });

  useEffect(() => {
    apiGet<{ items: Documento[]; total: number; totalGeneral: number }>("/api/imputacion/documentos", {
      page,
      pageSize: 20,
      idContacto: filtrosAplicados.idContacto ?? undefined,
      fechaDesde: filtrosAplicados.fechaDesde || undefined,
      fechaHasta: filtrosAplicados.fechaHasta || undefined,
      estado: filtrosAplicados.estado || undefined,
    }).then((r) => {
      setDocumentos(r.items);
      setTotal(r.total);
      setTotalGeneral(r.totalGeneral);
    });
  }, [page, filtrosAplicados]);

  function aplicarFiltros(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    setFiltrosAplicados({ idContacto, fechaDesde, fechaHasta, estado });
  }

  function marcarCorridaAprobada(idCorrida: string) {
    setDocumentos((prev) =>
      prev.map((doc) => ({
        ...doc,
        lineas: doc.lineas.map((linea) => ({
          ...linea,
          fracciones: linea.fracciones.map((f) =>
            f.idCorrida === idCorrida ? { ...f, estado: "Aprobada" as const } : f
          ),
        })),
      }))
    );
  }

  function urlExportar() {
    const url = new URL("/api/imputacion/documentos/exportar", API_BASE_URL);
    if (filtrosAplicados.idContacto) url.searchParams.set("idContacto", String(filtrosAplicados.idContacto));
    if (filtrosAplicados.fechaDesde) url.searchParams.set("fechaDesde", filtrosAplicados.fechaDesde);
    if (filtrosAplicados.fechaHasta) url.searchParams.set("fechaHasta", filtrosAplicados.fechaHasta);
    if (filtrosAplicados.estado) url.searchParams.set("estado", filtrosAplicados.estado);
    return url.toString();
  }

  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <h1 className="text-2xl font-semibold">Imputación por documento comercial</h1>
      <p className="mt-1 text-sm text-ink-secondary">
        Para la oficina del contador: cada línea de factura/NC/ND con su clasificación manual y la propuesta del
        motor desplegable debajo.
      </p>

      <div className="mt-4">
        <FilterBar onSubmit={aplicarFiltros}>
          <FilterField label="Proveedor">
            <ContactoSelect
              value={idContacto}
              razonSocial={proveedorNombre}
              onChange={(id, nombre) => {
                setIdContacto(id);
                setProveedorNombre(nombre);
              }}
              placeholder="Buscar proveedor…"
            />
          </FilterField>
          <FilterField label="Fecha desde">
            <input type="date" className={filterInputClass} value={fechaDesde} onChange={(e) => setFechaDesde(e.target.value)} />
          </FilterField>
          <FilterField label="Fecha hasta">
            <input type="date" className={filterInputClass} value={fechaHasta} onChange={(e) => setFechaHasta(e.target.value)} />
          </FilterField>
          <FilterField label="Estado">
            <select className={filterInputClass} value={estado} onChange={(e) => setEstado(e.target.value as Estado | "")}>
              <option value="">Todos</option>
              <option value="Pendiente">Pendiente</option>
              <option value="Aprobada">Aprobada</option>
              <option value="RequiereIntervencion">Requiere intervención</option>
            </select>
          </FilterField>
          <FilterSubmitButton />
        </FilterBar>
        <a
          href={urlExportar()}
          className="mt-3 inline-block rounded-md border border-border px-3 py-1.5 text-sm text-ink-secondary hover:bg-surface-sunken"
        >
          Exportar a Excel {filtrosAplicados.idContacto || filtrosAplicados.fechaDesde || filtrosAplicados.fechaHasta ? "(con estos filtros)" : ""}
        </a>
      </div>

      <div className="mt-6 space-y-6">
        {documentos.map((doc) => (
          <div key={doc.idCompra} className="rounded-md border border-border">
            <div className="flex items-center justify-between border-b border-border bg-surface-sunken px-4 py-2">
              <span className="text-sm font-medium">
                {doc.tipoDocumento} {doc.numeroDocumento} — {doc.proveedor ?? "—"}
              </span>
              <span className="text-xs text-ink-secondary">
                {new Date(doc.fecha).toLocaleDateString("es-AR")} · {doc.moneda}
              </span>
            </div>
            <div className="px-4 py-3">
              <ResumenImputacion filas={doc.lineas.flatMap((linea) => linea.fracciones.map((f) => ({
                ...f, producto: linea.producto, idDetalleCompra: linea.idDetalleCompra,
              })))} />
            </div>
            <details className="px-4 pb-3">
            <summary className="cursor-pointer py-2 text-sm font-medium">Detalle por insumo y clasificación manual</summary>
            <table className="w-full">
              <thead>
                <tr className="text-left text-xs text-ink-secondary">
                  <th className="py-1.5 pl-6">Producto/Servicio</th>
                  <th className="py-1.5">Cantidad</th>
                  <th className="py-1.5">Campaña manual</th>
                  <th className="py-1.5">Centro/Rubro manual</th>
                  <th className="py-1.5">Motor (ARS)</th>
                </tr>
              </thead>
              <tbody>
                {doc.lineas.map((linea) => (
                  <LineaRow key={linea.idDetalleCompra} linea={linea} onAprobada={marcarCorridaAprobada} />
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t border-border text-sm font-medium">
                  <td colSpan={4} className="py-1.5 pl-6 text-right">
                    Total documento
                  </td>
                  <td className="py-1.5">{doc.totalDocumento.toLocaleString("es-AR")}</td>
                </tr>
              </tfoot>
            </table>
            </details>
          </div>
        ))}
        {documentos.length === 0 && <p className="text-sm text-ink-secondary">No hay documentos con imputación todavía.</p>}
        {documentos.length > 0 && (
          <div className="flex items-center justify-end gap-2 rounded-md border border-border bg-surface-sunken px-4 py-2 text-sm font-medium">
            Total general (con estos filtros): {totalGeneral.toLocaleString("es-AR")}
          </div>
        )}
      </div>

      <div className="mt-4 flex items-center gap-2 text-sm">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => setPage((p) => p - 1)}
          className="rounded-md border border-border px-2 py-1 disabled:opacity-40"
        >
          ← Anterior
        </button>
        <span className="text-ink-secondary">
          Página {page} de {Math.max(1, Math.ceil(total / 20))} ({total} documentos)
        </span>
        <button
          type="button"
          disabled={page * 20 >= total}
          onClick={() => setPage((p) => p + 1)}
          className="rounded-md border border-border px-2 py-1 disabled:opacity-40"
        >
          Siguiente →
        </button>
      </div>
    </main>
  );
}
