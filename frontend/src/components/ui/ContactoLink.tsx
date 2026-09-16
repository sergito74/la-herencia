import Link from "next/link";

/**
 * Link uniforme desde cualquier nombre de contacto (proveedor, comprador,
 * empleado, organismo, arrendatario) hacia su cuenta corriente — vínculo
 * transversal más barato y de mayor valor percibido del sistema
 * (design/erp-module-architecture.md §3.5): "clic en cualquier nombre →
 * ver todo lo que le compramos/vendimos/pagamos".
 */
export function ContactoLink({
  idContacto,
  razonSocial,
  tipoContacto,
}: {
  idContacto: number | null | undefined;
  razonSocial: string | null | undefined;
  tipoContacto?: string | null;
}) {
  if (idContacto == null) return <>{razonSocial ?? "—"}</>;

  const params = new URLSearchParams({ idContacto: String(idContacto) });
  if (razonSocial) params.set("razonSocial", razonSocial);
  if (tipoContacto) params.set("tipoContacto", tipoContacto);

  return (
    <Link href={`/finanzas/cuentas-corrientes?${params.toString()}`} className="text-finance underline">
      {razonSocial ?? `#${idContacto}`}
    </Link>
  );
}
