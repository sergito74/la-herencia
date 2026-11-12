"use client";

import { useParams } from "next/navigation";

import { FormularioResultados } from "@/components/resultado-cultivo/FormularioResultados";
import { PageHeader } from "@/components/ui/PageHeader";

/** Resultado de un cultivo (enlaces desde el consolidado de campaña): mismo formato que FrmResultados de Access. */
export default function DetalleResultadoCultivoPage() {
  const params = useParams<{ idCampania: string; idCultivo: string }>();
  const idCampania = Number(params.idCampania);
  const idCultivo = Number(params.idCultivo);
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Resultado de cultivo" volver="/produccion/resultado-cultivo" />
      {Number.isInteger(idCampania) && Number.isInteger(idCultivo)
        ? <FormularioResultados idCultivo={idCultivo} idCampania={idCampania} />
        : <p className="text-sm text-status-danger">Cultivo o campaña inválidos.</p>}
    </main>
  );
}
