"use client";

import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import {
  fetchContactos,
  fetchMovimientos,
  fetchSaldo,
  urlExportarCuenta,
  type Contacto,
  type MovimientoCuentaCorriente,
} from "@/services/cuentasCorrientesApi";
import { OrigenMovimiento } from "@/components/cuentas-corrientes/OrigenMovimiento";
import { Breadcrumb } from "@/components/ui/Breadcrumb";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { FilterBar, FilterField, FilterSubmitButton, filterInputClass } from "@/components/ui/FilterBar";
import { KpiCard } from "@/components/ui/KpiCard";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatMoneda } from "@/lib/format";

// Valores confirmados de `Tipo Contacto` contra datos reales (data-model.md).
const TIPOS_CONTACTO = [
  "Banco",
  "Comprador",
  "Consignatario",
  "Empleado",
  "Multiple",
  "Organismo",
  "Proveedor",
  "Tarjeta de Credito",
];

const COLUMNS: DataTableColumn<MovimientoCuentaCorriente>[] = [
  { key: "fecha", header: "Fecha", numeric: true, sortValue: (m) => m.fecha, render: (m) => m.fecha ?? "—" },
  { key: "documento", header: "Documento", render: (m) => m.documento ?? "—" },
  { key: "numeroDocumento", header: "Nro. documento", render: (m) => m.numeroDocumento ?? "—" },
  {
    key: "deuda",
    header: "Deuda (débito)",
    align: "right",
    numeric: true,
    sortValue: (m) => m.deuda,
    render: (m) => (
      <span className="text-status-danger">{m.deuda ? formatMoneda(m.deuda) : "—"}</span>
    ),
  },
  {
    key: "credito",
    header: "Crédito (haber)",
    align: "right",
    numeric: true,
    sortValue: (m) => m.credito,
    render: (m) => (
      <span className="text-status-success">{m.credito ? formatMoneda(m.credito) : "—"}</span>
    ),
  },
  {
    key: "saldoParcial",
    header: "Saldo",
    align: "right",
    numeric: true,
    render: (m) => (
      <span className={m.saldoParcial != null && m.saldoParcial < 0 ? "text-status-danger" : "text-status-success"}>
        {m.saldoParcial != null ? formatMoneda(m.saldoParcial) : "—"}
      </span>
    ),
  },
  { key: "origen", header: "Origen", render: (m) => <OrigenMovimiento origen={m.origen} /> },
];

/**
 * Búsqueda de contacto + saldo + movimientos (US1: FR-001, FR-002, FR-003,
 * FR-004, FR-005, FR-012, FR-013; US3: filtro por tipo, FR-002). Read-only:
 * no hay affordance de crear/editar/eliminar (FR-010). Migrado al design
 * system "Tierra & Cultivo" (design/agroux-frontend-redesign.md §5.3).
 */
export function CuentaCorriente() {
  const searchParams = useSearchParams();
  const [q, setQ] = useState("");
  const [tipoContacto, setTipoContacto] = useState("");
  const [appliedQ, setAppliedQ] = useState("");
  const [appliedTipoContacto, setAppliedTipoContacto] = useState("");
  const [selected, setSelected] = useState<Contacto | null>(null);

  // Vínculo transversal (design/erp-module-architecture.md §3.5): un link
  // "ver cuenta corriente" desde cualquier módulo (Compras, Arrendamientos,
  // Ventas de Hacienda, Impuestos, Remuneraciones) llega acá con
  // ?idContacto=&razonSocial=&tipoContacto= y selecciona el contacto de
  // una, sin pasar por el buscador.
  useEffect(() => {
    const idContacto = searchParams.get("idContacto");
    if (!idContacto) return;
    setSelected({
      idContacto: Number(idContacto),
      razonSocial: searchParams.get("razonSocial"),
      tipoContacto: searchParams.get("tipoContacto"),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const [fechaDesde, setFechaDesde] = useState("");
  const [fechaHasta, setFechaHasta] = useState("");
  const [appliedDates, setAppliedDates] = useState({ fechaDesde: "", fechaHasta: "" });
  const [page, setPage] = useState(1);
  const pageSize = 50;

  const {
    data: contactosData,
    isLoading: loadingContactos,
    isError: errorContactos,
  } = useQuery({
    queryKey: ["cc-contactos", appliedQ, appliedTipoContacto],
    queryFn: () =>
      fetchContactos({
        q: appliedQ || undefined,
        tipoContacto: appliedTipoContacto || undefined,
      }),
    enabled: appliedQ.length > 0 || appliedTipoContacto.length > 0,
  });

  const { data: saldo, isLoading: loadingSaldo } = useQuery({
    queryKey: ["cc-saldo", selected?.idContacto],
    queryFn: () => fetchSaldo(selected!.idContacto),
    enabled: selected !== null,
  });

  const {
    data: movimientos,
    isLoading: loadingMovimientos,
    isError: errorMovimientos,
  } = useQuery({
    queryKey: ["cc-movimientos", selected?.idContacto, appliedDates, page, pageSize],
    queryFn: () =>
      fetchMovimientos(selected!.idContacto, {
        fechaDesde: appliedDates.fechaDesde || undefined,
        fechaHasta: appliedDates.fechaHasta || undefined,
        page,
        pageSize,
      }),
    enabled: selected !== null,
  });

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    setAppliedQ(q);
    setAppliedTipoContacto(tipoContacto);
    setSelected(null);
  }

  function handleSelectContacto(contacto: Contacto) {
    setSelected(contacto);
    setPage(1);
    setAppliedDates({ fechaDesde: "", fechaHasta: "" });
    setFechaDesde("");
    setFechaHasta("");
  }

  function handleDateFilterSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    setAppliedDates({ fechaDesde, fechaHasta });
  }

  return (
    <div className="space-y-6">
      {selected && (
        <Breadcrumb
          items={[
            { label: "Cuentas corrientes", href: undefined },
            { label: selected.razonSocial ?? "—" },
          ]}
        />
      )}

      <FilterBar onSubmit={handleSearchSubmit}>
        <FilterField label="Contacto">
          <input
            className={filterInputClass}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Razón social"
          />
        </FilterField>
        <FilterField label="Tipo de contacto">
          <select
            className={filterInputClass}
            value={tipoContacto}
            onChange={(e) => setTipoContacto(e.target.value)}
          >
            <option value="">Todos</option>
            {TIPOS_CONTACTO.map((tipo) => (
              <option key={tipo} value={tipo}>
                {tipo}
              </option>
            ))}
          </select>
        </FilterField>
        <FilterSubmitButton />
      </FilterBar>

      {loadingContactos && <LoadingState rows={3} />}
      {errorContactos && <ErrorState message="Ocurrió un error al buscar contactos." />}

      {contactosData && !selected && (
        <>
          {contactosData.items.length === 0 && (
            <div className="rounded-md border border-border bg-surface p-6 text-center text-sm text-ink-secondary">
              Sin resultados para esta búsqueda.
            </div>
          )}
          {contactosData.items.length > 0 && (
            <ul className="divide-y divide-border rounded-md border border-border bg-surface">
              {contactosData.items.map((contacto) => (
                <li key={contacto.idContacto}>
                  <button
                    type="button"
                    className="w-full px-4 py-2 text-left text-sm hover:bg-surface-sunken"
                    onClick={() => handleSelectContacto(contacto)}
                  >
                    {contacto.razonSocial ?? "—"}{" "}
                    <span className="text-ink-secondary">({contacto.tipoContacto ?? "sin tipo"})</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}

      {selected && (
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-4 rounded-md border border-border bg-surface p-4">
            <div>
              <h2 className="text-lg font-semibold text-ink-primary">
                {selected.razonSocial ?? "—"}
              </h2>
              <p className="text-sm text-ink-secondary">{selected.tipoContacto ?? "sin tipo"}</p>
            </div>
            <KpiCard
              label="Saldo"
              value={
                loadingSaldo
                  ? "…"
                  : saldo?.saldoParcial != null
                    ? formatMoneda(saldo.saldoParcial)
                    : "—"
              }
              tone={
                saldo?.saldoParcial == null ? "neutral" : saldo.saldoParcial < 0 ? "danger" : "success"
              }
            />
            <a
              href={urlExportarCuenta(selected.idContacto, {
                fechaDesde: appliedDates.fechaDesde || undefined,
                fechaHasta: appliedDates.fechaHasta || undefined,
              })}
              className="rounded border border-border px-3 py-1.5 text-sm hover:bg-surface-sunken"
            >
              Exportar a Excel
            </a>
            <button
              type="button"
              className="text-sm text-finance underline"
              onClick={() => setSelected(null)}
            >
              Cambiar contacto
            </button>
          </div>

          <FilterBar onSubmit={handleDateFilterSubmit}>
            <FilterField label="Fecha desde">
              <input
                type="date"
                className={filterInputClass}
                value={fechaDesde}
                onChange={(e) => setFechaDesde(e.target.value)}
              />
            </FilterField>
            <FilterField label="Fecha hasta">
              <input
                type="date"
                className={filterInputClass}
                value={fechaHasta}
                onChange={(e) => setFechaHasta(e.target.value)}
              />
            </FilterField>
            <FilterSubmitButton>Filtrar</FilterSubmitButton>
          </FilterBar>

          {loadingMovimientos && <LoadingState />}
          {errorMovimientos && <ErrorState message="Ocurrió un error al obtener movimientos." />}

          {movimientos && (
            <DataTable
              columns={COLUMNS}
              rows={movimientos.items}
              keyField={(m) => `${m.fecha}-${m.numeroDocumento}-${m.documento}`}
              emptyMessage="Sin movimientos para el período seleccionado."
              page={movimientos.page}
              pageSize={movimientos.pageSize}
              total={movimientos.total}
              onPageChange={setPage}
            />
          )}
        </div>
      )}
    </div>
  );
}
