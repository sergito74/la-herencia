"use client";

import { useEffect, useState } from "react";

import { API_BASE_URL, apiGet } from "@/services/apiClient";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { FilterBar, FilterField, FilterSubmitButton, filterInputClass } from "@/components/ui/FilterBar";

interface Fraccion {
  idPropuesta: number;
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
}

function etiquetaDestino(f: Fraccion): string {
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

function LineaRow({ linea }: { linea: Linea }) {
  const [abierta, setAbierta] = useState(false);
  const tiene = linea.fracciones.length > 0;

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
        <td className="py-1.5">{linea.cantidad}</td>
        <td className="py-1.5">{linea.campaniaManual ?? "—"}</td>
        <td className="py-1.5">{linea.centroCostoManual ?? linea.rubroManual ?? "—"}</td>
        <td className="py-1.5 text-ink-secondary">{tiene ? `${linea.fracciones.length} fracción(es)` : "sin propuesta"}</td>
      </tr>
      {abierta &&
        linea.fracciones.map((f) => (
          <tr key={f.idPropuesta} className="border-t border-border bg-surface-sunken text-xs">
            <td className="py-1 pl-14 text-ink-secondary">↳ {etiquetaDestino(f)}</td>
            <td className="py-1" colSpan={2}>
              {f.importe.toLocaleString("es-AR")}
            </td>
            <td className="py-1">{f.origen}</td>
            <td className="py-1">{badgeEstado(f.estado)}</td>
          </tr>
        ))}
    </>
  );
}

export default function DocumentosImputacionPage() {
  const [documentos, setDocumentos] = useState<Documento[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const [idContacto, setIdContacto] = useState<number | null>(null);
  const [proveedorNombre, setProveedorNombre] = useState<string | null>(null);
  const [fechaDesde, setFechaDesde] = useState("");
  const [fechaHasta, setFechaHasta] = useState("");
  const [filtrosAplicados, setFiltrosAplicados] = useState<{ idContacto: number | null; fechaDesde: string; fechaHasta: string }>({
    idContacto: null,
    fechaDesde: "",
    fechaHasta: "",
  });

  useEffect(() => {
    apiGet<{ items: Documento[]; total: number }>("/api/imputacion/documentos", {
      page,
      pageSize: 20,
      idContacto: filtrosAplicados.idContacto ?? undefined,
      fechaDesde: filtrosAplicados.fechaDesde || undefined,
      fechaHasta: filtrosAplicados.fechaHasta || undefined,
    }).then((r) => {
      setDocumentos(r.items);
      setTotal(r.total);
    });
  }, [page, filtrosAplicados]);

  function aplicarFiltros(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    setFiltrosAplicados({ idContacto, fechaDesde, fechaHasta });
  }

  function urlExportar() {
    const url = new URL("/api/imputacion/documentos/exportar", API_BASE_URL);
    if (filtrosAplicados.idContacto) url.searchParams.set("idContacto", String(filtrosAplicados.idContacto));
    if (filtrosAplicados.fechaDesde) url.searchParams.set("fechaDesde", filtrosAplicados.fechaDesde);
    if (filtrosAplicados.fechaHasta) url.searchParams.set("fechaHasta", filtrosAplicados.fechaHasta);
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
            <table className="w-full">
              <thead>
                <tr className="text-left text-xs text-ink-secondary">
                  <th className="py-1.5 pl-6">Producto/Servicio</th>
                  <th className="py-1.5">Cantidad</th>
                  <th className="py-1.5">Campaña manual</th>
                  <th className="py-1.5">Centro/Rubro manual</th>
                  <th className="py-1.5">Motor</th>
                </tr>
              </thead>
              <tbody>
                {doc.lineas.map((linea) => (
                  <LineaRow key={linea.idDetalleCompra} linea={linea} />
                ))}
              </tbody>
            </table>
          </div>
        ))}
        {documentos.length === 0 && <p className="text-sm text-ink-secondary">No hay documentos con imputación todavía.</p>}
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
