"""One-off: carga las boletas reales de UATRE (organismo IdContacto=315,
IdTipoImpuesto=15) que faltaban en dbo.Impuestos, leídas de
`C:\\Users\\Sergio\\Dropbox\\Giamigli de Bolivar SA\\Sindicato Rural`
(2026-09-29).

Dos casos:
- Completa el importe/número de documento de 8 filas placeholder que ya
  existían (período 09/2024 a 04/2025, cargadas con Importe=NULL) — se
  actualizan por IdImpuesto, nunca se borran ni se tocan otras columnas.
- Inserta 16 filas nuevas para los períodos 05/2025 a 08/2026, que no
  tenían ninguna fila.

Importe = Total pagado (capital + intereses, cuando los hay — ej. 08/2025,
09/2025, 05/2026 tienen intereses por mora). Fecha = fecha de vencimiento
del comprobante (mismo criterio que ya usan las 8 filas placeholder
existentes, confirmado contra la real: IdImpuesto=1179 ya tenía
Fecha=2024-10-16, que es exactamente el vencimiento del período 09/2024).
"""

from src.db.connection import execute_write

IDCONTACTO_UATRE = 315
IDTIPOIMPUESTO_UATRE = 15

# (IdImpuesto, numeroDocumento, importe) — completa placeholders existentes
ACTUALIZAR = [
    (1179, "0023778038", 17595.82),
    (1180, "0024076019", 18617.51),
    (1181, "0024512713", 18738.99),
    (1182, "0024786392", 29082.59),
    (1183, "0025237963", 20073.78),
    (1184, "0025564964", 21889.02),
    (1185, "0025892882", 23307.24),
    (1186, "0026326192", 22352.66),
]

# (periodoLiquidado, fecha, numeroDocumento, importe) — filas nuevas
INSERTAR = [
    ("05 2025", "2025-06-16", "0026643973", 22351.24),
    ("06 2025", "2025-07-16", "0027106711", 34004.86),
    ("07 2025", "2025-08-16", "0027408201", 22351.24),
    ("08 2025", "2025-09-19", "0028033692", 24316.75),
    ("09 2025", "2025-10-20", "0028401979", 24132.16),
    ("10 2025", "2025-11-16", "0028569418", 27177.36),
    ("11 2025", "2025-12-16", "0028959060", 25748.91),
    ("12 2025", "2026-01-16", "0029369810", 40632.84),
    ("01 2026", "2026-02-16", "0029655724", 31977.33),
    ("02 2026", "2026-03-16", "0030058306", 25850.17),
    ("03 2026", "2026-04-16", "0030384585", 27301.77),
    ("04 2026", "2026-05-16", "0030725158", 27301.77),
    ("05 2026", "2026-06-17", "0031315306", 31765.80),
    ("06 2026", "2026-07-16", "0031632120", 54166.88),
    ("07 2026", "2026-08-16", "0031960027", 31781.20),
    ("08 2026", "2026-09-16", "0032379085", 31779.73),
]


def main() -> None:
    for id_impuesto, numero_documento, importe in ACTUALIZAR:
        filas = execute_write(
            "UPDATE dbo.Impuestos SET [Numero de documento] = ?, Importe = ? "
            "WHERE IdImpuesto = ? AND IdOrganismo = ? AND Importe IS NULL",
            (numero_documento, importe, id_impuesto, IDCONTACTO_UATRE),
        )
        print(f"UPDATE IdImpuesto={id_impuesto}: {filas} fila(s)")

    for periodo, fecha, numero_documento, importe in INSERTAR:
        filas = execute_write(
            "INSERT INTO dbo.Impuestos (Fecha, IdOrganismo, IdTipoImpuesto, [Periodo liquidado], [Numero de documento], Importe) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (fecha, IDCONTACTO_UATRE, IDTIPOIMPUESTO_UATRE, periodo, numero_documento, importe),
        )
        print(f"INSERT periodo={periodo}: {filas} fila(s)")


if __name__ == "__main__":
    main()
