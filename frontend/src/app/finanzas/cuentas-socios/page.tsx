import { redirect } from "next/navigation";

/** Las cuentas de socios viven ahora en «Cajas y socios» junto con las cajas de efectivo. */
export default function CuentasSociosPage() {
  redirect("/finanzas/cajas");
}
