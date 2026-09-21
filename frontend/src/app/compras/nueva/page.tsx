import { CompraForm } from "@/components/compras/CompraForm";

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
    importe: Number.isFinite(importe) && importe > 0 ? importe : undefined,
  };
  return (
    <main className="mx-auto max-w-none px-8 py-3">
      <CompraForm mode="alta" prefill={prefill} />
    </main>
  );
}
