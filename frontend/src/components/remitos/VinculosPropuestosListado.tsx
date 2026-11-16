"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { useToast } from "@/components/ui/Toast";
import { formatCantidad, formatFecha } from "@/lib/format";
import {
  descartarVinculosPropuestos,
  fetchVinculosPropuestos,
  grabarVinculosPropuestos,
  type VinculoPropuesto,
} from "@/services/remitosApi";

const clave = (v: VinculoPropuesto) => v.ids.join("-");

/** 050: vínculos remito ↔ factura propuestos por la regla de emparejamiento (mismo proveedor, producto o principio
 * activo y cantidad). Nada se graba hasta que el usuario los aprueba (regla de carga automática). */
export function VinculosPropuestosListado() {
  const { showToast } = useToast();
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["vinculos-propuestos"],
    queryFn: fetchVinculosPropuestos,
    staleTime: 0,
  });
  const [elegidos, setElegidos] = useState<Set<string>>(new Set());
  const [trabajando, setTrabajando] = useState(false);

  const conRemito = (data?.items ?? []).filter((v) => !v.sinRemito);
  const sinRemito = (data?.items ?? []).filter((v) => v.sinRemito);
  const todos = conRemito.length > 0 && conRemito.every((v) => elegidos.has(clave(v)));

  const alternar = (v: VinculoPropuesto) =>
    setElegidos((prev) => {
      const s = new Set(prev);
      if (s.has(clave(v))) s.delete(clave(v));
      else s.add(clave(v));
      return s;
    });

  const idsElegidos = () => conRemito.filter((v) => elegidos.has(clave(v))).flatMap((v) => v.ids);

  async function grabar() {
    setTrabajando(true);
    try {
      const r = await grabarVinculosPropuestos(idsElegidos());
      const errores = r.errores.flatMap((e) => e.mensajes);
      if (errores.length) showToast(`Se grabaron ${r.grabados} renglones. No se pudo: ${errores.join(" · ")}`, "danger");
      else showToast(`Se grabaron ${r.grabados} renglones vinculados.`, "success");
      setElegidos(new Set());
      await refetch();
    } catch {
      showToast("No se pudieron grabar los vínculos.", "danger");
    } finally {
      setTrabajando(false);
    }
  }

  async function descartar() {
    setTrabajando(true);
    try {
      await descartarVinculosPropuestos(idsElegidos());
      showToast("Propuestas descartadas.", "neutral");
      setElegidos(new Set());
      await refetch();
    } catch {
      showToast("No se pudieron descartar.", "danger");
    } finally {
      setTrabajando(false);
    }
  }

  const columnas: DataTableColumn<VinculoPropuesto>[] = [
    {
      key: "sel",
      header: "",
      render: (v) => (
        <input type="checkbox" aria-label="Elegir" checked={elegidos.has(clave(v))} onChange={() => alternar(v)} />
      ),
    },
    { key: "proveedor", header: "Proveedor", sortValue: (v) => v.proveedor, render: (v) => v.proveedor ?? "—" },
    {
      key: "factura",
      header: "Factura",
      numeric: true,
      sortValue: (v) => v.fechaFactura,
      render: (v) => (
        <Link className="text-finance underline" href={`/compras/${v.idCompra}/editar`}>
          {v.factura} · {formatFecha(v.fechaFactura)}
        </Link>
      ),
    },
    { key: "producto", header: "Producto", sortValue: (v) => v.producto, render: (v) => v.producto ?? "—" },
    {
      key: "cantidad",
      header: "Cantidad",
      numeric: true,
      align: "right",
      render: (v) => formatCantidad(v.cantidad),
    },
    {
      key: "remito",
      header: "Remito propuesto",
      numeric: true,
      sortValue: (v) => v.fechaRemito,
      render: (v) =>
        v.idRemito ? (
          <Link className="text-finance underline" href={`/produccion/remitos/${v.idRemito}`}>
            {v.remito} · {formatFecha(v.fechaRemito)}
          </Link>
        ) : (
          "—"
        ),
    },
    { key: "regla", header: "Cómo se encontró", render: (v) => v.regla ?? "—" },
  ];

  if (isLoading) return <LoadingState />;
  if (isError) return <ErrorState message="No se pudieron cargar los vínculos propuestos." onRetry={() => refetch()} />;

  return (
    <div className="space-y-4">
      <p className="text-sm text-ink-secondary">
        Remitos que coinciden con cada factura de insumos: mismo proveedor, mismo producto o principio activo y la
        misma cantidad. Revisá y grabá los que estén bien; con el vínculo, el costo de la factura sigue al insumo hasta
        la orden que lo usa.
      </p>
      <SoloLectura>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            className="rounded border border-border px-4 py-2 text-sm"
            onClick={() => setElegidos(todos ? new Set() : new Set(conRemito.map(clave)))}
          >
            {todos ? "Quitar todos" : "Elegir todos"}
          </button>
          <button
            type="button"
            className="rounded bg-finance px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
            disabled={trabajando || elegidos.size === 0}
            onClick={grabar}
          >
            Grabar vínculos elegidos ({elegidos.size})
          </button>
          <button
            type="button"
            className="rounded border border-border px-4 py-2 text-sm disabled:opacity-50"
            disabled={trabajando || elegidos.size === 0}
            onClick={descartar}
          >
            Descartar elegidos
          </button>
          <span className="text-sm text-ink-secondary">{conRemito.length} propuestas</span>
        </div>
      </SoloLectura>
      <DataTable
        columns={columnas}
        rows={conRemito}
        keyField={clave}
        emptyMessage="No hay vínculos propuestos para revisar."
        page={1}
        pageSize={Math.max(conRemito.length, 1)}
        total={conRemito.length}
        onPageChange={() => undefined}
      />
      {sinRemito.length > 0 && (
        <div className="space-y-2">
          <h2 className="text-base font-semibold">Facturas sin remito que coincida ({sinRemito.length})</h2>
          <DataTable
            columns={columnas.filter((c) => !["sel", "remito", "regla"].includes(c.key))}
            rows={sinRemito}
            keyField={clave}
            emptyMessage=""
            page={1}
            pageSize={Math.max(sinRemito.length, 1)}
            total={sinRemito.length}
            onPageChange={() => undefined}
          />
        </div>
      )}
    </div>
  );
}
