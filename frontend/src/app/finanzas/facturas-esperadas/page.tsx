"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { useState } from "react";
import { Tabs } from "@/components/ui/Tabs";
import { AlarmasFaltantes } from "@/components/facturas-faltantes/AlarmasFaltantes";
import { TableroFacturasEsperadas } from "@/components/facturas-faltantes/TableroFacturasEsperadas";

export default function FacturasEsperadasPage() {
  const [vista, setVista] = useState("tablero");
  return (
    <main className="mx-auto max-w-none space-y-3 px-6 py-3">
      <PageHeader titulo="Facturas esperadas" ayuda="Qué facturas de proveedores deberían haber llegado y cuáles faltan. Todo lo que aparece acá es para verificar con el comprobante: nada se carga ni cambia saldos solo." />
      <Tabs idBase="facturas-esperadas" activa={vista} onChange={setVista}
        tabs={[{ id: "tablero", label: "Proveedores que facturan seguido" }, { id: "alarmas", label: "Otras alarmas" }]}>
        {vista === "tablero" ? <TableroFacturasEsperadas /> : <AlarmasFaltantes />}
      </Tabs>
    </main>
  );
}
