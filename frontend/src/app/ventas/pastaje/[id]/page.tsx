import { notFound } from "next/navigation";
import { Suspense } from "react";

import { FichaContrato } from "@/components/pastaje/FichaContrato";

export const metadata = { title: "Contrato de pastaje" };

export default function ContratoPastajePage({ params }: { params: { id: string } }) {
  const id = Number(params.id);
  if (!Number.isInteger(id) || id <= 0) notFound();
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <Suspense>
        <FichaContrato id={id} />
      </Suspense>
    </main>
  );
}
