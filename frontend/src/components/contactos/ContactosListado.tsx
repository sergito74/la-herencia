"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  actualizarContacto,
  crearContacto,
  fetchContactos,
  TIPOS_CONTACTO,
  type Contacto,
  type ContactoInput,
  type TipoContacto,
} from "@/services/contactosApi";
import { ContactoForm } from "@/components/contactos/ContactoForm";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { FilterBar, FilterField, FilterSubmitButton, filterInputClass } from "@/components/ui/FilterBar";
import { SideDrawer } from "@/components/ui/SideDrawer";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { useToast } from "@/components/ui/Toast";

/**
 * CRUD real de Contactos (módulo fundacional: usado por Compras, Ventas,
 * Finanzas, Personal para seleccionar contactos vía combo en vez de texto
 * libre — ver `ContactoSelect`). Escribe exclusivamente contra `WC`.
 */
export function ContactosListado() {
  const [q, setQ] = useState("");
  const [tipoContacto, setTipoContacto] = useState<TipoContacto | "">("");
  const [appliedFilters, setAppliedFilters] = useState<{ q: string; tipoContacto: string }>({
    q: "",
    tipoContacto: "",
  });
  const [page, setPage] = useState(1);
  const pageSize = 50;
  const [editing, setEditing] = useState<Contacto | "new" | null>(null);

  const queryClient = useQueryClient();
  const { showToast } = useToast();

  // Sin filtro no se pide nada — con ~500 contactos reales, mostrar de
  // entrada los primeros 50 en orden alfabético daba la falsa impresión de
  // que "faltaban" proveedores que en realidad estaban más adelante en el
  // alfabeto, sin filtrar (pedido explícito del usuario, 2026-09-17).
  const hayFiltro = appliedFilters.q !== "" || appliedFilters.tipoContacto !== "";
  const queryKey = ["contactos", appliedFilters, page];
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey,
    queryFn: () =>
      fetchContactos({
        q: appliedFilters.q || undefined,
        tipoContacto: appliedFilters.tipoContacto || undefined,
        page,
        pageSize,
      }),
    enabled: hayFiltro,
  });

  const saveMutation = useMutation({
    mutationFn: (input: ContactoInput) =>
      editing && editing !== "new"
        ? actualizarContacto(editing.idContacto, input)
        : crearContacto(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contactos"] });
      showToast(
        editing && editing !== "new" ? "Contacto actualizado." : "Contacto creado.",
        "success"
      );
      setEditing(null);
    },
    onError: () => {
      showToast("No se pudo guardar el contacto. Intentá de nuevo.", "danger");
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    setAppliedFilters({ q, tipoContacto });
  }

  const COLUMNS: DataTableColumn<Contacto>[] = [
    {
      key: "razonSocial",
      header: "Razón social",
      sortValue: (c) => c.razonSocial,
      render: (c) => c.razonSocial ?? "—",
    },
    {
      key: "tipoContacto",
      header: "Tipo",
      sortValue: (c) => c.tipoContacto,
      render: (c) => c.tipoContacto ?? "—",
    },
    { key: "cuit", header: "CUIT/CUIL", render: (c) => c.cuit ?? "—" },
    {
      key: "editar",
      header: "",
      align: "right",
      render: (c) => (
        <button
          type="button"
          onClick={() => setEditing(c)}
          className="rounded-sm border border-border px-2 py-0.5 text-xs text-ink-secondary hover:border-border-strong hover:text-ink-primary"
        >
          Editar
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <FilterBar onSubmit={handleSubmit}>
        <FilterField label="Buscar">
          <input
            className={filterInputClass}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Razón social o CUIT"
          />
        </FilterField>
        <FilterField label="Tipo">
          <select
            className={filterInputClass}
            value={tipoContacto}
            onChange={(e) => setTipoContacto(e.target.value as TipoContacto | "")}
          >
            <option value="">Todos</option>
            {TIPOS_CONTACTO.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </FilterField>
        <FilterSubmitButton />
        <button
          type="button"
          onClick={() => setEditing("new")}
          className="ml-auto rounded-sm bg-agro px-4 py-2 text-sm text-white hover:opacity-90"
        >
          + Nuevo contacto
        </button>
      </FilterBar>

      {!hayFiltro && (
        <EmptyState message="Buscá por razón social/CUIT o elegí un tipo para ver contactos." />
      )}
      {hayFiltro && isLoading && <LoadingState />}
      {hayFiltro && isError && (
        <ErrorState message="Ocurrió un error al buscar contactos." onRetry={() => refetch()} />
      )}

      {hayFiltro && data && (
        <DataTable
          columns={COLUMNS}
          rows={data.items}
          keyField={(c) => c.idContacto}
          emptyMessage="Sin resultados para esta búsqueda."
          page={data.page}
          pageSize={data.pageSize}
          total={data.total}
          onPageChange={setPage}
        />
      )}

      <SideDrawer
        open={editing !== null}
        onClose={() => setEditing(null)}
        title={editing && editing !== "new" ? "Editar contacto" : "Nuevo contacto"}
      >
        <ContactoForm
          initial={editing !== "new" ? editing : null}
          onSubmit={(input) => saveMutation.mutate(input)}
          onCancel={() => setEditing(null)}
          isSaving={saveMutation.isPending}
        />
      </SideDrawer>
    </div>
  );
}
