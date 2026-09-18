"use client";

import { useParams, useRouter } from "next/navigation";

import { TarjetaCuentaCorriente } from "@/components/tarjetas/TarjetaCuentaCorriente";

export default function TarjetaCuentaCorrientePage() {
  const params = useParams<{ idTarjeta: string }>();
  const idTarjeta = Number(params.idTarjeta);
  const router = useRouter();

  return (
    <main className="mx-auto max-w-none px-8 py-3">
      <button
        type="button"
        onClick={() => router.push("/finanzas/tarjetas")}
        className="text-sm text-finance underline"
      >
        ← Volver a Tarjetas
      </button>
      <h1 className="mt-1 text-base font-semibold">Cuenta corriente de tarjeta</h1>
      <div className="mt-2">
        <TarjetaCuentaCorriente idTarjeta={idTarjeta} />
      </div>
    </main>
  );
}
