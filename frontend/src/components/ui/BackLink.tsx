import Link from "next/link";

/** Link de "volver atrás" consistente en toda la app — mismo estilo que ya
 * usaban Compras/Ventas, ahora en cada pantalla que no lo tenía. */
export function BackLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} className="text-sm text-finance underline">
      ← {children}
    </Link>
  );
}
