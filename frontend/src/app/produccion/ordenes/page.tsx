"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { OrdenesListado } from "@/components/ordenes/OrdenesListado";
import { TipoLaborAdmin } from "@/components/ordenes/TipoLaborAdmin";
import { RemitosSubNav } from "@/components/remitos/RemitosSubNav";
import { BackLink } from "@/components/ui/BackLink";
import { fetchTiposLabor } from "@/services/ordenesApi";

export default function OrdenesPage() {
  const qc = useQueryClient();
  const [mostrarLabores, setMostrarLabores] = useState(false);
  const { data: tiposLabor, refetch } = useQuery({ queryKey: ["ordenes", "tipos-labor"], queryFn: fetchTiposLabor, enabled: mostrarLabores });

  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/">Volver al inicio</BackLink>
      <div className="mt-2 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Órdenes de trabajo</h1>
        <button type="button" onClick={() => setMostrarLabores((v) => !v)} className="rounded border border-border px-3 py-1.5 text-sm hover:bg-surface-sunken">
          {mostrarLabores ? "Ocultar" : "Administrar"} tipos de labor
        </button>
      </div>
      <div className="mt-4">
        <RemitosSubNav />
      </div>
      {mostrarLabores && tiposLabor && (
        <div className="mt-4">
          <TipoLaborAdmin
            tiposLabor={tiposLabor}
            onCreado={() => {
              refetch();
              qc.invalidateQueries({ queryKey: ["ordenes", "catalogos"] });
            }}
          />
        </div>
      )}
      <div className="mt-6">
        <OrdenesListado />
      </div>
    </main>
  );
}
