import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState } from "@/components/ui/States";

export default function Page() {
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Controles ganaderos" />
      <EmptyState message="Próximamente" />
    </main>
  );
}
