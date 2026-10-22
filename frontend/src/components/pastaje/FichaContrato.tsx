"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { Breadcrumb } from "@/components/ui/Breadcrumb";
import { KpiCard } from "@/components/ui/KpiCard";
import { SideDrawer } from "@/components/ui/SideDrawer";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Tabs } from "@/components/ui/Tabs";
import { formatFecha } from "@/lib/format";
import { anularContrato, fichaContrato, finalizarContrato, type ContratoFicha } from "@/services/pastajeApi";

import { BitacoraHacienda } from "./BitacoraHacienda";
import { ContratoForm } from "./ContratoForm";
import { Facturas } from "./Facturas";
import { IndicePanel } from "./IndicePanel";
import { Liquidaciones } from "./Liquidaciones";
import { btnSecundario, inputCls, mesTexto, pesos, tarifaTexto, tonoContrato, tonoEstadoMes } from "./comunes";

type Tab = "condiciones" | "bitacora" | "liquidaciones" | "facturas" | "indice";
const TABS: { id: Tab; label: string }[] = [
  { id: "condiciones", label: "Condiciones" },
  { id: "bitacora", label: "Bitácora" },
  { id: "liquidaciones", label: "Liquidaciones" },
  { id: "facturas", label: "Facturas" },
  { id: "indice", label: "Índice INMAG" },
];

export function FichaContrato({ id }: { id: number }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const tab = (TABS.find((t) => t.id === params.get("tab"))?.id ?? "condiciones") as Tab;
  const periodo = params.get("periodo") ?? undefined;
  const ir = (t: Tab, extra: Record<string, string> = {}) => router.replace(`${pathname}?${new URLSearchParams({ tab: t, ...extra })}`);
  const q = useQuery({ queryKey: ["pastaje", "ficha", id], queryFn: () => fichaContrato(id) });

  if (q.isLoading) return <LoadingState />;
  if (q.isError || !q.data) return <ErrorState message={(q.error as Error)?.message ?? "No se pudo cargar"} onRetry={() => q.refetch()} />;
  const c = q.data;
  const cerrados = c.meses.filter((m) => m.estado !== "En curso");
  const alertas = c.meses.flatMap((m) => m.alertas.map((a) => ({ periodo: m.periodo, texto: a, estado: m.estado })));
  const suma = (k: "liquidado" | "facturado" | "cobrado" | "saldo") => cerrados.reduce((s, m) => s + Number(m[k] ?? 0), 0);
  const curso = c.meses.find((m) => m.estado === "En curso");

  return (
    <div className="space-y-5">
      <Breadcrumb items={[{ label: "Ventas" }, { label: "Pastaje", href: "/ventas/pastaje" }, { label: c.cliente }]} />
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Pastaje · {c.cliente}</h1>
          <p className="mt-1 text-ink-secondary">
            {c.establecimiento ?? "La Herencia"} · desde {formatFecha(c.fechaInicio)}
            {c.fechaFin ? ` hasta ${formatFecha(c.fechaFin)}` : ""} · {c.tarifas.map((t) => tarifaTexto(t)).join(" · ")}
          </p>
        </div>
        <StatusBadge label={c.estado} tone={tonoContrato(c.estado)} />
      </header>

      {alertas.length > 0 && (
        <ul role="status" className="space-y-1 rounded-md border border-status-warning bg-status-warning-bg p-3 text-sm text-status-warning">
          {alertas.map((a, i) => (
            <li key={i}>
              ⚠ {mesTexto(a.periodo)}: {a.texto}{" "}
              <button
                className="underline"
                onClick={() =>
                  a.texto.includes("índice") ? ir("indice", { periodo: a.periodo.slice(0, 7) }) :
                  a.estado === "Liquidado sin factura" ? ir("facturas") : ir("liquidaciones", { periodo: a.periodo.slice(0, 7) })
                }
              >
                Resolver
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <KpiCard label="Mes en curso (estimado)" value={pesos(curso?.devengado)} />
        <KpiCard label="Liquidado (neto)" value={pesos(suma("liquidado"))} />
        <KpiCard label="Facturado (neto)" value={pesos(suma("facturado"))} />
        <KpiCard label="Cobrado" value={pesos(suma("cobrado"))} />
        <KpiCard label="Saldo a cobrar" value={pesos(suma("saldo"))} tone={suma("saldo") > 0 ? "warning" : "success"} />
      </div>

      <Tabs tabs={TABS.map((t) => ({ ...t, aviso: t.id === "condiciones" ? alertas.length : undefined }))} activa={tab} onChange={(t) => ir(t)} idBase="pastaje">
        {tab === "condiciones" && <Condiciones c={c} irLiquidar={(p) => ir("liquidaciones", { periodo: p })} />}
        {tab === "bitacora" && <BitacoraHacienda contrato={c} />}
        {tab === "liquidaciones" && <Liquidaciones contrato={c} periodoInicial={periodo} />}
        {tab === "facturas" && <Facturas contrato={c} />}
        {tab === "indice" && <IndicePanel periodoInicial={periodo} />}
      </Tabs>
    </div>
  );
}

function Condiciones({ c, irLiquidar }: { c: ContratoFicha; irLiquidar: (p: string) => void }) {
  const cache = useQueryClient();
  const [editar, setEditar] = useState(false);
  const [cierre, setCierre] = useState<"finalizar" | "anular" | null>(null);
  const [fecha, setFecha] = useState("");
  const [motivo, setMotivo] = useState("");
  const cambiar = useMutation({
    mutationFn: () => (cierre === "finalizar" ? finalizarContrato(c.id, fecha, motivo || "Fin del contrato", c.version) : anularContrato(c.id, motivo, c.version)),
    onSuccess: () => {
      setCierre(null);
      cache.invalidateQueries({ queryKey: ["pastaje"] });
    },
  });
  const filas: [string, string | null][] = [
    ["Cliente", `${c.cliente}${c.cuit ? ` (CUIT ${c.cuit})` : ""}`],
    ["Empresa", "Giamigli de Bolívar S.A."],
    ["Establecimiento", c.establecimiento ?? "La Herencia"],
    ["Vigencia", `${formatFecha(c.fechaInicio)} – ${c.fechaFin ? formatFecha(c.fechaFin) : "sin fecha de fin"}`],
    ["Modalidad de cobro", "Mes vencido · contado"],
    ["IVA", `${Number(c.alicuotaIva).toString().replace(".", ",")}%`],
    ["Índice", c.tarifas.some((t) => t.tipoTarifa === "kg_novillo") ? "INMAG (Mercado Agroganadero de Cañuelas), promedio de los días con hacienda en el campo" : "Precio fijo"],
    ["Infraestructura", c.clausulaInfraestructura],
    ["Sanidad", c.clausulaSanidad],
    ["Mortandad", c.clausulaMortandad],
    ["Otras cláusulas", c.otrasClausulas],
    ["Contrato escrito", c.archivoContrato ?? "Sin contrato escrito"],
  ];
  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Condiciones del acuerdo</h2>
          {c.estado === "vigente" && (
            <SoloLectura>
              <div className="flex gap-2">
                <button className={btnSecundario} onClick={() => setEditar(true)}>Editar</button>
                <button className={btnSecundario} onClick={() => setCierre("finalizar")}>Finalizar</button>
                <button className={btnSecundario} onClick={() => setCierre("anular")}>Anular</button>
              </div>
            </SoloLectura>
          )}
        </div>
        <dl className="divide-y divide-border rounded-md border border-border bg-surface text-sm">
          {filas.map(([k, v]) => (
            <div key={k} className="grid grid-cols-[10rem_1fr] gap-3 px-3 py-2">
              <dt className="text-ink-secondary">{k}</dt>
              <dd className="whitespace-pre-wrap">{v || "—"}</dd>
            </div>
          ))}
        </dl>
        <h3 className="pt-2 font-semibold">Tarifas</h3>
        <ul className="space-y-1 text-sm">
          {c.tarifas.map((t) => (
            <li key={t.id}>
              Categoría {t.idTipoHacienda}: {tarifaTexto(t)} · rige desde {formatFecha(t.vigenteDesde)}
            </li>
          ))}
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Devengado, liquidado, facturado y cobrado por mes</h2>
        <div className="overflow-x-auto rounded-md border border-border">
          <table className="min-w-full text-sm">
            <thead className="bg-surface-muted text-left text-xs uppercase text-ink-secondary">
              <tr>
                <th className="px-3 py-2">Mes</th>
                <th className="px-3 py-2 text-right">Devengado</th>
                <th className="px-3 py-2 text-right">Liquidado</th>
                <th className="px-3 py-2 text-right">Facturado</th>
                <th className="px-3 py-2 text-right">Cobrado</th>
                <th className="px-3 py-2 text-right">Saldo</th>
                <th className="px-3 py-2">Estado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {c.meses.map((m) => (
                <tr key={m.periodo}>
                  <td className="px-3 py-2 capitalize">{mesTexto(m.periodo)}</td>
                  <td className="font-data px-3 py-2 text-right tabular-nums">{pesos(m.devengado)}</td>
                  <td className="font-data px-3 py-2 text-right tabular-nums">
                    {pesos(m.liquidado)}
                    {m.diferencia && <span className="block text-xs text-status-danger">dif. {pesos(m.diferencia)}</span>}
                  </td>
                  <td className="font-data px-3 py-2 text-right tabular-nums">{pesos(m.facturado)}</td>
                  <td className="font-data px-3 py-2 text-right tabular-nums">{pesos(m.cobrado)}</td>
                  <td className="font-data px-3 py-2 text-right tabular-nums">{pesos(m.saldo)}</td>
                  <td className="px-3 py-2">
                    <StatusBadge label={m.estado} tone={tonoEstadoMes(m.estado)} />
                    {m.estado === "Sin liquidar" && (
                      <button className="ml-2 text-xs underline" onClick={() => irLiquidar(m.periodo.slice(0, 7))}>
                        Liquidar
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-ink-secondary">
          Importes netos de IVA. El mes en curso se estima con la hacienda y el INMAG hasta hoy. <Link className="underline" href="/ventas/pastaje">Volver a contratos</Link>
        </p>
      </section>

      <SideDrawer open={editar} onClose={() => setEditar(false)} title="Editar contrato" maxWidthClass="max-w-2xl">
        <ContratoForm contrato={c} onListo={() => setEditar(false)} />
      </SideDrawer>
      <SideDrawer open={cierre !== null} onClose={() => setCierre(null)} title={cierre === "finalizar" ? "Finalizar contrato" : "Anular contrato"}>
        <form
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            cambiar.mutate();
          }}
        >
          {cierre === "finalizar" ? (
            <label className="block text-sm">
              Fecha de fin (con la hacienda ya egresada)
              <input type="date" required className={inputCls} value={fecha} onChange={(e) => setFecha(e.target.value)} />
            </label>
          ) : (
            <p className="text-sm">Solo se puede anular un contrato sin liquidaciones confirmadas (por ejemplo, cargado por error).</p>
          )}
          <label className="block text-sm">
            Motivo
            <input required={cierre === "anular"} className={inputCls} value={motivo} onChange={(e) => setMotivo(e.target.value)} />
          </label>
          {cambiar.error && <p role="alert" className="text-sm text-status-danger">{(cambiar.error as Error).message}</p>}
          <button className="rounded-sm bg-status-danger px-4 py-2 text-sm text-white" disabled={cambiar.isPending}>
            Confirmar
          </button>
        </form>
      </SideDrawer>
    </div>
  );
}
