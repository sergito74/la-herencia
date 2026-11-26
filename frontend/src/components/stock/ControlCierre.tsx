"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";

import { MarcaRevisado } from "@/components/ui/MarcaRevisado";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatCantidad, formatFecha } from "@/lib/format";
import { apiGet, apiPost } from "@/services/apiClient";
import { SoloLectura } from "@/components/auth/SoloLectura";

interface RemitoSinFactura {
  idRemito: number;
  fecha: string;
  remito: string;
  proveedor: string | null;
  productos: string[];
}
interface UsadoSinRemito {
  idProducto: number;
  producto: string;
  unidad: string | null;
  ordenes: { idOrdenTrabajo: number; fecha: string; cantidad: number }[];
}

interface ConsumoSinCosto {
  idProducto: number;
  producto: string;
  unidad: string | null;
  cantidad: number;
}
interface FacturaSobreVinculada {
  idCompra: number;
  documento: string;
  fecha: string;
  proveedor: string | null;
  renglon: string;
  cantidad: number;
  vinculada: number;
}
interface VinculoQueNoCorresponde {
  idRemito: number;
  remito: string;
  fecha: string;
  proveedor: string | null;
  producto: string | null;
  idCompra: number;
  documento: string;
  proveedorDocumento: string | null;
  motivo: string;
}

const fetchPendientes = () =>
  apiGet<{
    remitosSinFactura: RemitoSinFactura[];
    usadosSinRemito: UsadoSinRemito[];
    consumosSinCosto?: ConsumoSinCosto[];
    facturasSobreVinculadas?: FacturaSobreVinculada[];
    vinculosQueNoCorresponden?: VinculoQueNoCorresponde[];
  }>("/api/stock/pendientes-carga");

/** 050: lo que falta cargar para que el costo de los insumos cierre. Solo acciones concretas, por documento. */
interface Aceptado {
  idAceptado: number;
  tipo: "sin_factura" | "vinculo" | "sin_costo";
  idRemito: number | null;
  remito: string | null;
  fecha: string | null;
  proveedor: string | null;
  documento: string | null;
  producto: string | null;
  motivo: string;
  usuario: string | null;
  aceptado: string;
}

type Marca = { tipo: Aceptado["tipo"]; idRemito?: number; idCompra?: number; idProducto?: number };

/** 24/11/2026: excepción aprobada = marca en los datos (quién, cuándo, motivo), no una lista en el código. */
function BotonAceptar({ marca }: { marca: Marca }) {
  const qc = useQueryClient();
  return (
    <MarcaRevisado onAceptar={async (motivo) => {
      await apiPost("/api/stock/pendientes-carga/aceptar", { ...marca, motivo });
      qc.invalidateQueries({ queryKey: ["pendientes-carga"] });
      qc.invalidateQueries({ queryKey: ["pendientes-aceptados"] });
    }} />
  );
}

const TIPO_ACEPTADO: Record<Aceptado["tipo"], string> = {
  sin_factura: "Remito sin factura", vinculo: "Vínculo a otro documento", sin_costo: "Consumo sin costo",
};

function Aceptados() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["pendientes-aceptados"], queryFn: () => apiGet<Aceptado[]>("/api/stock/pendientes-carga/aceptados") });
  const quitar = useMutation({
    mutationFn: (id: number) => apiPost(`/api/stock/pendientes-carga/aceptados/${id}/quitar`, {}),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["pendientes-carga"] }); qc.invalidateQueries({ queryKey: ["pendientes-aceptados"] }); },
  });
  const filas = q.data ?? [];
  if (!filas.length) return null;
  return (
    <details className="rounded border bg-white text-sm">
      <summary className="cursor-pointer p-3 font-medium">Revisados y aceptados ({filas.length})</summary>
      <ul className="divide-y">
        {filas.map((a) => (
          <li key={a.idAceptado} className="flex flex-wrap items-center justify-between gap-2 p-3">
            <span>
              <strong>{TIPO_ACEPTADO[a.tipo]}</strong> · {a.producto ?? `${a.proveedor ?? ""} remito ${a.remito ?? ""}${a.fecha ? ` del ${formatFecha(a.fecha)}` : ""}`}
              {a.documento ? ` → ${a.documento}` : ""} — {a.motivo}
              <span className="text-xs text-ink-secondary"> ({a.usuario ?? "—"}, {formatFecha(a.aceptado)})</span>
            </span>
            <SoloLectura>
              <button type="button" disabled={quitar.isPending} className="text-xs text-ink-secondary underline" onClick={() => quitar.mutate(a.idAceptado)}>
                Quitar la marca
              </button>
            </SoloLectura>
          </li>
        ))}
      </ul>
    </details>
  );
}

export function ControlCierre() {
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["pendientes-carga"], queryFn: fetchPendientes, staleTime: 0 });
  if (isLoading) return <LoadingState />;
  if (isError) return <ErrorState message="No se pudieron consultar los pendientes." onRetry={() => refetch()} />;
  const remitos = data?.remitosSinFactura ?? [];
  const usados = data?.usadosSinRemito ?? [];
  const sinCosto = data?.consumosSinCosto ?? [];
  const sobre = data?.facturasSobreVinculadas ?? [];
  const ajenos = data?.vinculosQueNoCorresponden ?? [];

  if (!remitos.length && !usados.length && !sinCosto.length && !sobre.length && !ajenos.length) {
    return (
      <div className="space-y-3">
        <p className="rounded border bg-white p-4 text-sm">No hay nada pendiente de carga.</p>
        <Aceptados />
      </div>
    );
  }
  return (
    <div className="space-y-6">
      {remitos.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-base font-semibold">Facturas que faltan cargar</h2>
          <p className="text-sm text-ink-secondary">Llegó la mercadería y no hay factura. Cargala y vinculala al remito.</p>
          <ul className="divide-y rounded border bg-white text-sm">
            {remitos.map((r) => (
              <li key={r.idRemito} className="flex flex-wrap items-center justify-between gap-2 p-3">
                <span>
                  <strong>{r.proveedor}</strong> · remito {r.remito} del {formatFecha(r.fecha)} · {r.productos.join(", ")}
                </span>
                <span className="flex items-center gap-3">
                  <BotonAceptar marca={{ tipo: "sin_factura", idRemito: r.idRemito }} />
                  <Link className="text-finance underline" href={`/produccion/remitos/${r.idRemito}`}>
                    Abrir el remito
                  </Link>
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
      {usados.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-base font-semibold">Insumos usados sin remito de entrada</h2>
          <p className="text-sm text-ink-secondary">Una orden usó un producto que nunca entró al galpón: falta el remito o la orden tiene otro producto.</p>
          <ul className="divide-y rounded border bg-white text-sm">
            {usados.flatMap((u) =>
              u.ordenes.map((o) => (
                <li key={`${u.idProducto}-${o.idOrdenTrabajo}`} className="flex flex-wrap items-center justify-between gap-2 p-3">
                  <span>
                    <strong>{u.producto}</strong>: {formatCantidad(o.cantidad)} {u.unidad ?? ""} en la orden N° {o.idOrdenTrabajo} del {formatFecha(o.fecha)}
                  </span>
                  <Link className="text-finance underline" href={`/produccion/ordenes/${o.idOrdenTrabajo}`}>
                    Abrir la orden
                  </Link>
                </li>
              )),
            )}
          </ul>
        </section>
      )}
      {ajenos.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-base font-semibold">Remitos vinculados a un documento que no corresponde</h2>
          <p className="text-sm text-ink-secondary">
            El remito está vinculado a una factura de otro proveedor, a una nota de débito o crédito, o a un renglón que no se imputa. Cambiá el vínculo a la
            factura de compra de ese remito.
          </p>
          <ul className="divide-y rounded border bg-white text-sm">
            {ajenos.map((v) => (
              <li key={`${v.idRemito}-${v.idCompra}`} className="flex flex-wrap items-center justify-between gap-2 p-3">
                <span>
                  <strong>{v.proveedor}</strong> · remito {v.remito} del {formatFecha(v.fecha)} · {v.producto} → {v.documento} de {v.proveedorDocumento} ({v.motivo})
                </span>
                <span className="flex items-center gap-3">
                  <BotonAceptar marca={{ tipo: "vinculo", idRemito: v.idRemito, idCompra: v.idCompra }} />
                  <Link className="text-finance underline" href={`/produccion/remitos/${v.idRemito}`}>
                    Abrir el remito
                  </Link>
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
      {sobre.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-base font-semibold">Facturas vinculadas por más de lo facturado</h2>
          <p className="text-sm text-ink-secondary">Un renglón de factura está vinculado a remitos por más cantidad de la que tiene: esa mercadería se costearía dos veces.</p>
          <ul className="divide-y rounded border bg-white text-sm">
            {sobre.map((f) => (
              <li key={`${f.idCompra}-${f.renglon}`} className="flex flex-wrap items-center justify-between gap-2 p-3">
                <span>
                  <strong>{f.proveedor}</strong> · {f.documento} del {formatFecha(f.fecha)} · {f.renglon}: facturado {formatCantidad(f.cantidad)}, vinculado{" "}
                  {formatCantidad(f.vinculada)}
                </span>
                <Link className="text-finance underline" href={`/compras/${f.idCompra}/editar`}>
                  Abrir la factura
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
      {sinCosto.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-base font-semibold">Insumos usados sin costo</h2>
          <p className="text-sm text-ink-secondary">
            Las órdenes usaron mercadería de un remito que no tiene factura: ese consumo no llega con costo a los cultivos. Se resuelve cargando y vinculando la
            factura del remito (ver arriba).
          </p>
          <ul className="divide-y rounded border bg-white text-sm">
            {sinCosto.map((c) => (
              <li key={c.idProducto} className="flex flex-wrap items-center justify-between gap-2 p-3">
                <span><strong>{c.producto}</strong>: {formatCantidad(c.cantidad)} {c.unidad ?? ""} sin costo</span>
                <BotonAceptar marca={{ tipo: "sin_costo", idProducto: c.idProducto }} />
              </li>
            ))}
          </ul>
        </section>
      )}
      <Aceptados />
    </div>
  );
}
