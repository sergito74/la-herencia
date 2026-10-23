"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { SoloLectura } from "@/components/auth/SoloLectura";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatCantidad, formatFecha, formatMoneda } from "@/lib/format";
import { fetchSaldoCaja, listarArqueosCaja, monedaCaja, type CajaSlug } from "@/services/cajasEfectivoApi";
import { fetchSocios } from "@/services/cuentasSociosApi";

const CAJAS: { slug: CajaSlug; nombre: string; detalle: string }[] = [
  { slug: "giamigli-sa", nombre: "Caja Giamigli SA", detalle: "Efectivo de la empresa" },
  { slug: "giamigli-dolares", nombre: "Caja Giamigli US$", detalle: "Tenencia y movimientos de billetes en dólares" },
  { slug: "campo-chica", nombre: "Caja chica del campo", detalle: "Gastos menores en La Herencia" },
];

function TarjetaCaja({ slug, nombre, detalle }: (typeof CAJAS)[number]) {
  const saldo = useQuery({ queryKey: ["caja-efectivo-saldo", slug], queryFn: () => fetchSaldoCaja(slug) });
  const arqueo = useQuery({ queryKey: ["caja-arqueos", slug, 1], queryFn: () => listarArqueosCaja(slug) });
  const ultimo = arqueo.data?.items[0];
  const valor = saldo.data?.saldo ?? 0;
  return (
    <article className="flex flex-col justify-between rounded-md border border-border bg-surface p-4">
      <div>
        <h3 className="font-semibold">{nombre}</h3>
        <p className="text-sm text-ink-secondary">{detalle}</p>
        <p className={`font-data mt-3 text-2xl font-semibold ${valor < 0 ? "text-status-danger" : "text-ink-primary"}`}>
          {saldo.isLoading ? "…" : saldo.isError ? "—" : formatMoneda(valor, monedaCaja(slug))}
        </p>
        <p className="mt-1 text-xs text-ink-secondary">
          {ultimo ? `Último arqueo ${formatFecha(ultimo.fechaCorte)} · ${ultimo.estado}` : "Sin arqueos registrados"}
        </p>
      </div>
      <div className="mt-4 flex gap-2">
        <Link href={`/finanzas/cajas-efectivo/${slug}`} className="rounded-sm border border-border px-3 py-1.5 text-sm hover:bg-surface-sunken">
          Ver movimientos
        </Link>
        <SoloLectura>
          <Link href={`/finanzas/cajas-efectivo/${slug}?nuevo=1`} className="rounded-sm bg-agro px-3 py-1.5 text-sm text-white hover:opacity-90">
            + Movimiento
          </Link>
        </SoloLectura>
      </div>
    </article>
  );
}

export function CajasResumen() {
  const socios = useQuery({ queryKey: ["cuentas-socios"], queryFn: fetchSocios });
  return (
    <div className="space-y-8">
      <section>
        <h2 className="mb-3 text-lg font-semibold">Cajas de efectivo</h2>
        <div className="grid gap-4 md:grid-cols-3">
          {CAJAS.map((c) => (
            <TarjetaCaja key={c.slug} {...c} />
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold">Cuentas de socios y Condominio</h2>
        <p className="mb-3 text-sm text-ink-secondary">
          Deuda actualizada = kg de novillo × INMAG de hoy + US$ × dólar BNA de hoy. Positivo: el socio le debe a la empresa; negativo: a favor del socio.
        </p>
        {socios.isLoading && <LoadingState />}
        {socios.isError && <ErrorState message="No se pudieron cargar las cuentas de socios." onRetry={() => socios.refetch()} />}
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {socios.data?.socios.map((s) => {
            const a = s.actualizada;
            const deuda = a?.deudaActualizada ?? s.saldo;
            return (
              <article key={s.idSocio} className="rounded-md border border-border bg-surface p-4">
                <Link href={`/finanzas/cuentas-socios/${s.idSocio}`} className="hover:underline">
                <h3 className="font-semibold">{s.idSocio === 3 ? "Condominio LSC" : s.nombre}</h3></Link>
                <p className={`font-data mt-2 text-2xl font-semibold ${deuda > 0 ? "text-status-danger" : deuda < 0 ? "text-status-success" : ""}`}>
                  {formatMoneda(deuda)}
                </p>
                <p className="text-xs text-ink-secondary">{deuda > 0 ? "Le debe a la empresa" : deuda < 0 ? "A favor del socio" : "Sin saldo"}</p>
                {a && (
                  <p className="font-data mt-2 text-sm text-ink-secondary">
                    {formatCantidad(a.kgCarne)} kg · {formatMoneda(a.dolares, "Dolares")}
                    {a.mutuoUSD !== 0 && ` · mutuo ${formatMoneda(a.mutuoUSD, "Dolares")}`}
                  </p>
                )}
                {s.idSocio === 3 && <div className="mt-3 flex flex-wrap gap-3 text-sm"><Link className="underline" href="/finanzas/cuentas-socios/3">Cuenta con Giamigli</Link><Link className="underline" href="/finanzas/cajas-efectivo/condominio-lsc">Movimientos vinculados</Link></div>}
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}
