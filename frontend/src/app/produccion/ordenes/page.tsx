"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { OrdenesListado } from "@/components/ordenes/OrdenesListado";
import { TipoLaborAdmin } from "@/components/ordenes/TipoLaborAdmin";
import { PageHeader } from "@/components/ui/PageHeader";
import { SideDrawer } from "@/components/ui/SideDrawer";
import { fetchTiposLabor } from "@/services/ordenesApi";

export default function OrdenesPage() {
  const qc = useQueryClient();
  const [mostrarLabores, setMostrarLabores] = useState(false);
  const { data: tiposLabor, refetch } = useQuery({ queryKey: ["ordenes", "tipos-labor"], queryFn: fetchTiposLabor, enabled: mostrarLabores });

  return (
    <main className="mx-auto flex max-w-none flex-col px-6 py-3">
      <PageHeader titulo="Órdenes de trabajo" volver="/" ayuda="Tocá una fila para ver el resumen de la orden; 'Abrir' lleva a la orden completa.">
        <button type="button" onClick={() => setMostrarLabores(true)} className="rounded border border-border px-3 py-1.5 text-sm hover:bg-surface-sunken">
          Tipos de labor
        </button>
        <Link href="/produccion/ordenes/nuevo" className="rounded bg-finance px-3 py-1.5 text-sm text-white">
          + Nueva orden
        </Link>
      </PageHeader>
      <SideDrawer open={mostrarLabores} onClose={() => setMostrarLabores(false)} title="Tipos de labor">
        {tiposLabor && (
          <TipoLaborAdmin
            tiposLabor={tiposLabor}
            onCreado={() => {
              refetch();
              qc.invalidateQueries({ queryKey: ["ordenes", "catalogos"] });
              qc.invalidateQueries({ queryKey: ["ordenes-catalogos"] });
            }}
          />
        )}
      </SideDrawer>
      <OrdenesListado />
    </main>
  );
}
