import { ContactosListado } from "@/components/contactos/ContactosListado";
import { BackLink } from "@/components/ui/BackLink";

export const metadata = {
  title: "Contactos",
};

export default function ContactosPage() {
  return (
    <main className="mx-auto max-w-none px-8 py-6">
      <BackLink href="/">Volver al inicio</BackLink>
      <h1 className="mt-2 text-2xl font-semibold">Contactos</h1>
      <p className="mt-1 text-ink-secondary">
        Clientes, proveedores, compradores, consignatarios, empleados e instituciones —
        base de datos maestra usada por Compras, Ventas, Finanzas y Personal.
      </p>
      <div className="mt-6">
        <ContactosListado />
      </div>
    </main>
  );
}
