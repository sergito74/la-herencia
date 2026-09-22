"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { RemitoDetalleView } from "@/components/remitos/RemitoDetalleView";

export default function RemitoDetallePage() {
  const params = useParams<{ idRemito: string }>();
  return (
    <main className="mx-auto max-w-6xl px-8 py-6">
      <Link href="/produccion/remitos" className="text-sm text-finance underline">
        ← Remitos
      </Link>
      <div className="mt-3">
        <RemitoDetalleView idRemito={Number(params.idRemito)} />
      </div>
    </main>
  );
}
