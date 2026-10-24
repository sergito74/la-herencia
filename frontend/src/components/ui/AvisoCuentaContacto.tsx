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
    titulo: "Sergio como SOCIO — solo identifica movimientos de banco",
    texto:
      "Transferencias que no son sueldo: compensaciones, retiros, aportes y préstamos. La cuenta oficial de Sergio, " +
      "valuada en US$ y kg, es su cuenta de socio. Los sueldos van al contacto 375.",
  },
  390: {
    titulo: "Lucy como SOCIA — solo identifica movimientos de banco",
    texto: "La cuenta oficial de Lucy, valuada en US$ y kg, es su cuenta de socio.",
  },
  549: {
    titulo: "Condominio LSC — solo identifica movimientos de banco",
    texto: "La cuenta oficial del Condominio con Giamigli, valuada en US$ y kg, es su cuenta de socio.",
  },
};

/** Contacto «lado bancario» → socio (igual que backend cuentas_socios/contactos.py). Su saldo en pesos no es deuda. */
export const SOCIO_DE_CONTACTO: Record<number, number> = { 5670: 1, 390: 2, 549: 3 };

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
      {idContacto != null && SOCIO_DE_CONTACTO[idContacto] && (
        <p className="mt-1">
          El saldo en pesos de esta cuenta corriente <strong>no es la deuda del socio</strong>.{" "}
          <a className="underline" href={`/finanzas/cuentas-socios/${SOCIO_DE_CONTACTO[idContacto]}`}>Ver la cuenta de socio</a>
        </p>
      )}
    </div>
  );
}
