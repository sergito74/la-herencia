"use client";

import { PageHeader } from "@/components/ui/PageHeader";

import { useParams, useRouter } from "next/navigation";

import { TarjetaCuentaTabla } from "@/components/tarjetas-cuenta/TarjetaCuentaTabla";

export default function TarjetaCuentaCorrientePage() {
  const params = useParams<{ idTarjeta: string }>();
  const idTarjeta = Number(params.idTarjeta);
  const router = useRouter();

  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo={<>Cuenta corriente de tarjeta</>} onVolver={() => router.push("/finanzas/tarjetas")} />
      <div className="mt-2">
        <TarjetaCuentaTabla idTarjeta={idTarjeta} />
      </div>
    </main>
  );
}
