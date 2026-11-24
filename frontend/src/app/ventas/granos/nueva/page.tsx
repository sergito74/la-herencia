import { VentaGranosForm } from "@/components/ventas-granos/VentaGranosForm";
import { BackLink } from "@/components/ui/BackLink";

export const metadata = {
  title: "Nueva venta de granos",
};

type Params = Record<string, string | string[] | undefined>;

const uno = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v);

export default function NuevaVentaGranosPage({ searchParams }: { searchParams: Params }) {
  // Alta desde "Cargar venta de granos" de un aviso de Documentos nuevos: PDF y datos del portal (24/11/2026).
  const idContacto = Number(uno(searchParams.idContacto));
  const prefill = {
    idConsignatario: Number.isFinite(idContacto) && idContacto > 0 ? idContacto : null,
    consignatario: uno(searchParams.proveedor) ?? null,
    fecha: uno(searchParams.fecha),
    numeroDocumento: uno(searchParams.numeroDocumento),
    documentoOriginal: uno(searchParams.documentoOriginal),
  };
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <BackLink href="/ventas/granos">Volver a Ventas de granos</BackLink>
      <div className="mt-2">
        <VentaGranosForm mode="alta" prefill={prefill} />
      </div>
    </main>
  );
}
