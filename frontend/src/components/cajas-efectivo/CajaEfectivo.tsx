"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { SideDrawer } from "@/components/ui/SideDrawer";
import { Tabs } from "@/components/ui/Tabs";

import {
  fetchMovimientosCaja,
  fetchSaldoCaja,
  type CajaSlug,
  type MovimientoCajaEfectivo,
} from "@/services/cajasEfectivoApi";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { KpiCard } from "@/components/ui/KpiCard";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatFecha, formatMoneda } from "@/lib/format";
import { SoloLectura } from "@/components/auth/SoloLectura";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { fetchSocios } from "@/services/cuentasSociosApi";
import { listarArqueosCaja, monedaCaja, TIPOS_CAJA } from "@/services/cajasEfectivoApi";
import { OperacionCajaForm } from "./OperacionCajaForm";
import { ArqueoCajaPanel } from "./ArqueoCajaPanel";
import { ImportacionCajaPanel } from "./ImportacionCajaPanel";
import { DetalleOperacionCaja } from "./DetalleOperacionCaja";

const NOMBRES: Record<CajaSlug, string> = {
  "giamigli-dolares": "Caja de efectivo — Giamigli US$",
  "giamigli-sa": "Caja de efectivo — Giamigli SA",
  "campo-chica": "Caja chica del campo",
  "condominio-lsc": "Movimientos del Condominio con Giamigli",
};

const COLUMNS: DataTableColumn<MovimientoCajaEfectivo>[] = [
  { key: "fecha", header: "Fecha", sortValue: (m) => m.fecha, render: (m) => formatFecha(m.fecha) },
  { key: "concepto", header: "Concepto", sortValue: (m) => m.concepto ?? "", render: (m) => m.concepto ?? "—" },
  { key: "detalle", header: "Detalle", sortValue: (m) => m.detalle ?? "", render: (m) => m.detalle ?? "—" },
  {
    key: "importe",
    header: "Importe",
    align: "right",
    numeric: true,
    sortValue: (m) => m.importe,
    render: (m) => (
      <span className={m.importe < 0 ? "text-status-danger" : "text-status-success"}>{formatMoneda(m.importe)}</span>
    ),
  },
  { key: "cuenta", header: "Cuenta", render: (m) => m.cuenta ?? "—" },
  { key: "saldo", header: "Saldo real de caja", align: "right", render: m => m.saldoCorridoDecimal == null ? "—" : formatMoneda(Number(m.saldoCorridoDecimal)) },
  { key: "estado", header: "Estado", render: m => m.anulada ? "Anulado" : m.idOperacion ? "Vigente" : "Histórico" },
  { key: "formaPago", header: "Forma de pago", render: (m) => m.formaPago ?? "—" },
];

/** Caja 038: operaciones, consulta, arqueos e importación con permisos existentes. */
export function CajaEfectivo({ caja }: { caja: CajaSlug }) {
  const esCondominio = caja === "condominio-lsc";
  const moneda = monedaCaja(caja);
  const columns = COLUMNS.map(c => c.key === "importe" ? { ...c, render: (m: MovimientoCajaEfectivo) => formatMoneda(m.importe, moneda) } : c.key === "saldo" ? { ...c, header: esCondominio ? "Neto acumulado" : "Saldo real de caja", render: (m: MovimientoCajaEfectivo) => m.saldoCorridoDecimal == null ? "—" : formatMoneda(Number(m.saldoCorridoDecimal), moneda) } : c);
  const [page, setPage] = useState(1);
  const params = useSearchParams();
  const [vista, setVista] = useState<"movimientos" | "arqueos" | "importar">("movimientos");
  const [nuevo, setNuevo] = useState(params.get("nuevo") === "1");
  useEffect(() => { if (params.get("nuevo") === "1") setNuevo(true); }, [params]);
  const [detalle, setDetalle] = useState<number | null>(null);
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [tipo, setTipo] = useState("");
  const [contacto, setContacto] = useState<number | null>(null);
  const [nombreContacto, setNombreContacto] = useState<string | null>(null);
  const [socio, setSocio] = useState(0);
  const [anulados, setAnulados] = useState(false);
  const pageSize = 50;
  const ultimo = useQuery({ queryKey: ["caja-arqueos", caja, 1], queryFn: () => listarArqueosCaja(caja), enabled: !esCondominio });
  const socios = useQuery({ queryKey: ["cuentas-socios"], queryFn: fetchSocios });

  const { data: saldo, isLoading: cargandoSaldo } = useQuery({
    queryKey: ["caja-efectivo-saldo", caja],
    queryFn: () => fetchSaldoCaja(caja),
  });

  const {
    data: movimientos,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["caja-efectivo-movimientos", caja, page, pageSize, desde, hasta, tipo, contacto, socio, anulados],
    queryFn: () => fetchMovimientosCaja(caja, { page, pageSize, desde, hasta, tipo, idContacto: contacto ?? undefined, idSocio: socio || undefined, incluirAnuladas: anulados }),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4 rounded-md border border-border bg-surface p-4">
        <h2 className="text-lg font-semibold text-ink-primary">{NOMBRES[caja]}</h2>
        <KpiCard
          label={esCondominio ? "Neto de movimientos vinculados" : "Saldo"}
          value={cargandoSaldo ? "…" : formatMoneda(saldo?.saldo ?? 0, moneda)}
          tone={esCondominio ? "neutral" : saldo && saldo.saldo < 0 ? "danger" : "success"}
        />
      </div>
      {caja === "condominio-lsc" && <p>Solo relaciones documentadas con Giamigli. Salidas del Condominio negativas; entradas positivas. El neto no representa el efectivo físico del Condominio ni su deuda o crédito con Giamigli, que se consulta en «Cuenta con Giamigli». Los gastos propios y las filas sin vínculo comprobado quedaron fuera de este registro.</p>}
      {!esCondominio && ultimo.data?.items[0] && <p>Último arqueo: {formatFecha(ultimo.data.items[0].fechaCorte)} · {ultimo.data.items[0].estado} · diferencia vigente {formatMoneda(Number(ultimo.data.items[0].diferenciaVigenteDecimal), moneda)}</p>}
      {!esCondominio && ultimo.isError && <p role="alert">No se pudo consultar el último arqueo. <button onClick={() => ultimo.refetch()}>Reintentar</button></p>}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-ink-secondary">{esCondominio ? "Pagos de gastos de Giamigli realizados por el Condominio. Los aportes y devoluciones se registran desde Cuenta con Giamigli." : moneda === "Dolares" ? "Tenencias, entradas y salidas de dólares billete, aportes y retiros de socios." : "Pagos, cobros, aportes y retiros de socios, traspasos, banco y gastos."} Un movimiento mal cargado se anula (queda en el historial) y se vuelve a cargar con «Corregir».</p>
        <SoloLectura><button className="rounded-sm bg-agro px-4 py-2 text-sm text-white hover:opacity-90" onClick={() => setNuevo(true)}>+ Nuevo movimiento</button></SoloLectura>
      </div>
      <SideDrawer open={nuevo} onClose={() => setNuevo(false)} title={`Nuevo movimiento — ${NOMBRES[caja]}`} maxWidthClass="max-w-3xl">
        <SoloLectura><OperacionCajaForm key={caja} caja={caja} onSaved={id => { setNuevo(false); setDetalle(id); }} /></SoloLectura>
      </SideDrawer>
      <SideDrawer open={detalle !== null} onClose={() => setDetalle(null)} title="Detalle, auditoría y anulación" maxWidthClass="max-w-2xl">
        {detalle && <DetalleOperacionCaja key={detalle} id={detalle} onClose={() => setDetalle(null)} />}
      </SideDrawer>
      <Tabs idBase="caja" activa={vista} onChange={setVista} tabs={esCondominio ? [{ id: "movimientos", label: "Movimientos vinculados" }, { id: "importar", label: "Comparar vínculos con la planilla" }] : [{ id: "movimientos", label: "Movimientos" }, { id: "arqueos", label: "Arqueos" }, { id: "importar", label: "Comparar con la planilla" }]}>
      {!esCondominio && vista === "arqueos" && <ArqueoCajaPanel key={caja} caja={caja} onOperation={setDetalle} />}
      {vista === "importar" && <SoloLectura><ImportacionCajaPanel /></SoloLectura>}
      {vista === "movimientos" && <><div className="grid gap-3 rounded border border-border p-3 md:grid-cols-3">
        <label>Desde<input className="block rounded border border-border p-2" type="date" value={desde} onChange={e => { setDesde(e.target.value); setPage(1); }} /></label>
        <label>Hasta<input className="block rounded border border-border p-2" type="date" value={hasta} onChange={e => { setHasta(e.target.value); setPage(1); }} /></label>
        <label>Tipo<select className="block rounded border border-border p-2" value={tipo} onChange={e => { setTipo(e.target.value); setPage(1); }}><option value="">Todos</option>{Object.entries(TIPOS_CAJA).map(([k, v]) => <option key={k} value={k}>{v}</option>)}<option value="diferencia_arqueo">Diferencia de arqueo</option></select></label>
        <ContactoSelect value={contacto} razonSocial={nombreContacto} label="Contacto" onChange={(id, nombre) => { setContacto(id); setNombreContacto(nombre); setPage(1); }} />
        <label>Socio<select className="block rounded border border-border p-2" value={socio} onChange={e => { setSocio(Number(e.target.value)); setPage(1); }}><option value={0}>Todos</option>{socios.data?.socios.map(s => <option key={s.idSocio} value={s.idSocio}>{s.nombre}</option>)}</select></label>
        <label><input type="checkbox" checked={anulados} onChange={e => { setAnulados(e.target.checked); setPage(1); }} /> Incluir anulados</label>
      </div>
      {movimientos && <p>{esCondominio ? "Neto anterior al período" : "Arrastre real"}: {formatMoneda(Number(movimientos.saldoAnteriorDecimal ?? 0), moneda)} · subtotal de movimientos filtrados: {formatMoneda(Number(movimientos.subtotalFiltradoDecimal ?? 0), moneda)}. {esCondominio ? "El neto acumulado" : "El saldo corrido"} incluye los movimientos ocultos por los filtros.</p>}

      {isLoading && <LoadingState />}
      {isError && <ErrorState message="Ocurrió un error al obtener los movimientos." onRetry={() => refetch()} />}

      {movimientos && (
        <DataTable
          columns={[...columns, { key: "operacion", header: "Origen", render: m => m.idOperacion ? <button className="underline" onClick={() => setDetalle(m.idOperacion!)}>Ver / anular / corregir</button> : m.numeroDocumento || m.formaPago || "Historia de planilla" }]}
          rows={movimientos.items}
          keyField={(m) => m.idMovimiento}
          emptyMessage="Sin movimientos registrados para esta caja."
          page={movimientos.page}
          pageSize={movimientos.pageSize}
          total={movimientos.total}
          onPageChange={setPage}
        />
      )}
      </>}
      </Tabs>
    </div>
  );
}
