"use client";

import { useState } from "react";

import { MEDIO_LABELS, MovimientosPorMedio } from "@/components/tesoreria/MovimientosPorMedio";
import { CargaExcel } from "@/components/tesoreria/CargaExcel";
import type { Medio } from "@/services/tesoreriaApi";

const MEDIOS: Medio[] = [
  "bna",
  "galicia",
  "efectivo",
  "valores-propios",
  "valores-recibidos",
  "tarjetas",
];

export default function TesoreriaPage() {
  const [medio, setMedio] = useState<Medio>("bna");

  return (
    <main className="mx-auto max-w-6xl p-8">
      <h1 className="text-2xl font-semibold">Tesorería</h1>
      <p className="mt-1 text-slate-600">
        Movimientos por banco, caja, valores y tarjetas (solo lectura).
      </p>

      <div className="mt-6 flex flex-wrap gap-2">
        {MEDIOS.map((m) => (
          <button
            key={m}
            className={`rounded px-3 py-1.5 text-sm ${
              m === medio
                ? "bg-slate-900 text-white"
                : "border border-slate-300 text-slate-700 hover:bg-slate-100"
            }`}
            onClick={() => setMedio(m)}
          >
            {MEDIO_LABELS[m]}
          </button>
        ))}
      </div>

      <div className="mt-6">
        <MovimientosPorMedio medio={medio} />
      </div>

      <div className="mt-8">
        <CargaExcel />
      </div>
    </main>
  );
}
