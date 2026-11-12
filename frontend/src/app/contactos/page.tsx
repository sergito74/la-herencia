import { PageHeader } from "@/components/ui/PageHeader";
import { ContactosListado } from "@/components/contactos/ContactosListado";

export const metadata = {
  title: "Contactos",
};

export default function ContactosPage() {
  return (
    <main className="mx-auto max-w-none px-6 py-3">
      <PageHeader titulo="Contactos" ayuda="Clientes, proveedores, compradores, consignatarios, empleados e instituciones — base de datos maestra usada por Compras, Ventas, Finanzas y Personal." />
      <div className="mt-3">
        <ContactosListado />
      </div>
    </main>
  );
}
