import { CompraForm } from "@/components/compras/CompraForm";
import { PageHeader } from "@/components/ui/PageHeader";

export const metadata = {
  title: "Nueva compra",
};

type Params = Record<string, string | string[] | undefined>;

const uno = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v);

export default function NuevaCompraPage({ searchParams }: { searchParams: Params }) {
  // Datos opcionales para arrancar el alta precargada (ej. desde la conciliación de tarjetas).
  const idContacto = Number(uno(searchParams.idContacto));
  const importe = Number(uno(searchParams.importe));
  const prefill = {
    idContacto: Number.isFinite(idContacto) && idContacto > 0 ? idContacto : null,
    proveedorNombre: uno(searchParams.proveedor) ?? null,
    fecha: uno(searchParams.fecha),
    numeroDocumento: uno(searchParams.numeroDocumento),
    detalle: uno(searchParams.detalle),
    // Un reintegro de tarjeta (importe negativo) se carga como Nota de Crédito
    // en negativo (caso real 2026-10-02, Luvik S.A.).
    importe: Number.isFinite(importe) && importe !== 0 ? importe : undefined,
    // PDF ya bajado por la descarga de peajes (037).
    documentoOriginal: uno(searchParams.documentoOriginal),
  };
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Nueva compra" volver="/compras" ayuda="Factura, nota de crédito o débito de un proveedor: cabecera, renglones con su imputación y forma de pago." />
      <div>
        <CompraForm mode="alta" prefill={prefill} />
      </div>
    </main>
  );
}
