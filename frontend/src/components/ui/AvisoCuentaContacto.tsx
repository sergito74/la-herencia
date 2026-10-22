/** Alerta operativa sobre qué cuenta se está trabajando (Sergio, 22/10/2026): la
 * cuenta de Sergio está separada en EMPLEADO (375, solo sueldos) y SOCIO (5670,
 * lado bancario de su cuenta de socio). Cargar un movimiento en la equivocada
 * vuelve a mezclar sueldos con aportes/retiros. */

const AVISOS: Record<number, { titulo: string; texto: string }> = {
  375: {
    titulo: "Cuenta de Sergio como EMPLEADO",
    texto:
      "Solo recibos de sueldo, sus pagos y retenciones (debe cerrar en $0). Aportes, retiros, compensaciones " +
      "(\"Devolución por aporte\"), gastos particulares y retiros del Condominio van a \"Sergio Giamberardini (socio)\" " +
      "y a Cuentas de socios.",
  },
  5670: {
    titulo: "Cuenta de Sergio como SOCIO (lado bancario)",
    texto:
      "Transferencias que no son sueldo: compensaciones, retiros, aportes, préstamos y retiros del Condominio. " +
      "El registro valuado (kg novillo / US$) está en Cuentas de socios → Sergio. Los sueldos van al contacto 375.",
  },
};

export function avisoCuenta(idContacto: number | null | undefined) {
  return idContacto != null ? AVISOS[idContacto] : undefined;
}

export function AvisoCuentaContacto({ idContacto }: { idContacto: number | null | undefined }) {
  const aviso = avisoCuenta(idContacto);
  if (!aviso) return null;
  return (
    <div role="alert" className="rounded-md border-l-4 border-status-warning bg-status-warning/10 p-3 text-sm">
      <p className="font-semibold">⚠ {aviso.titulo}</p>
      <p className="text-ink-secondary">{aviso.texto}</p>
    </div>
  );
}
