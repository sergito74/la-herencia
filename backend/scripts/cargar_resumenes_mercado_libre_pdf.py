"""Carga los resúmenes de Mercado Libre (PDF) que faltan en `WC` (2026-09-26).

A diferencia de BNA/Galicia (Excel), Mercado Pago solo exporta resúmenes en
PDF con un formato simple y estable: Fecha, Descripción, ID de la operación,
Valor (signado), Saldo. Se parsea con `pdfplumber` reconstruyendo filas por
posición (`x0`/`top`) porque `extract_tables` no reconoce la grilla (sin
líneas dibujadas) y la descripción puede partirse en varias líneas.

Dedup / idempotencia: como el PDF no trae un id de resumen (a diferencia de
`Tarjetas_Resumenes.ResumenCodigo`), se usa como clave natural
(Fecha, IdOperacion, Importe, Saldo) — hay `UNIQUE` en la tabla con esa
misma clave (`crear_tabla_movimientos_mercado_libre.py`), así que correr
este script dos veces con los mismos PDF no duplica nada.

El proveedor/contacto de la descripción (texto libre: "Transferencia
recibida X", "Pago de servicio UATRE", etc.) se intenta resolver contra
`Contactos.[Razon Social]` por coincidencia exacta case-insensitive; sin
match, `IdContacto` queda NULL (se vincula a mano después, igual que
`cargar_resumenes_tarjetas_excel.py` — nunca adivina por similitud).

Excepción explícita (pedido del usuario, backlog post-025): "UATRE" es un
caso conocido y siempre igual — la descripción real nunca es exactamente
"UATRE" (viene como "Pago de servicio(s) UATRE"), así que la coincidencia
exacta nunca la resuelve. Si la palabra "UATRE" aparece en la descripción,
se asigna directo al contacto "UATRE" (mismo criterio que backfillea
`scripts/asignar_contacto_uatre_mercado_libre.py` sobre las filas ya
cargadas). No se generaliza a un substring-match para cualquier proveedor.

Por defecto corre en modo DRY-RUN. Requiere `--apply` para escribir, y aun
así NO EJECUTAR sin backup de `WC` verificado (Constitución, Principio II).

Uso (desde backend/):
  .venv\\Scripts\\python.exe -m scripts.cargar_resumenes_mercado_libre_pdf                # dry-run
  .venv\\Scripts\\python.exe -m scripts.cargar_resumenes_mercado_libre_pdf --apply         # escribe
"""

from __future__ import annotations

import argparse
import glob
import re

import pdfplumber

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, fetch_one

CVU_MERCADO_LIBRE = "0000003100045405413930"
CARPETA_RESUMENES = (
    r"C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Bancos\Mercado Libre\Resumenes\*\*.pdf"
)

DATE_RE = re.compile(r"^\d{2}-\d{2}-\d{4}$")
NUM_RE = re.compile(r"^-?[\d.]+,\d{2}$")
ID_RE = re.compile(r"^\d{6,}$")


def _parse_amount(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def _parse_fecha(s: str):
    d, m, y = s.split("-")
    return f"{y}-{m}-{d}"


_BLOCK_GAP = 15  # px: separa transacciones (~25-27px) de líneas de un mismo párrafo (~5-13px)


def _parse_pdf(path: str) -> list[dict]:
    """Reconstruye las filas de "Detalle de movimientos" por bloques.

    Cada transacción es un bloque de 1-3 líneas verticalmente contiguas
    (gap chico entre ellas); pdfplumber centra verticalmente las celdas
    Fecha/ID/Valor/Saldo dentro del bloque, así que esa línea puede quedar
    en el medio de una Descripción de varias líneas (no siempre es la
    primera ni la última) — agrupar por líneas sueltas (como se hacía
    antes) mezclaba la descripción de una transacción con la siguiente.
    Los bloques se separan por un salto vertical mucho mayor (~25px) que
    el interlineado dentro de un mismo párrafo (~5-13px).
    """
    with pdfplumber.open(path) as pdf:
        words = pdf.pages[0].extract_words()
    words = [w for w in words if 170 < w["top"] < 560]

    tops = sorted(set(round(w["top"], 1) for w in words))
    blocks_tops: list[list[float]] = []
    current_tops: list[float] = []
    last_top = None
    for top in tops:
        if last_top is not None and top - last_top > _BLOCK_GAP:
            blocks_tops.append(current_tops)
            current_tops = []
        current_tops.append(top)
        last_top = top
    if current_tops:
        blocks_tops.append(current_tops)

    txns: list[dict] = []
    for block_tops in blocks_tops:
        block_words = sorted(
            (w for w in words if round(w["top"], 1) in block_tops),
            key=lambda w: (w["top"], w["x0"]),
        )
        texts = [w["text"] for w in block_words]
        if texts[:1] == ["Fecha"] or "DETALLE" in texts:
            continue

        date_word = next((w for w in block_words if w["x0"] < 45 and DATE_RE.match(w["text"])), None)
        if date_word is None:
            continue  # bloque sin fecha (no debería pasar fuera de la cabecera)

        txn: dict = {"fecha": _parse_fecha(date_word["text"]), "desc_parts": [], "id_operacion": None, "valor": None, "saldo": None}
        nums: list[tuple[float, str]] = []
        for w in block_words:
            if w is date_word or w["text"] == "$":
                continue
            if ID_RE.match(w["text"]) and 150 <= w["x0"] < 260:
                txn["id_operacion"] = w["text"]
            elif NUM_RE.match(w["text"]):
                nums.append((w["x0"], w["text"]))
            elif 80 <= w["x0"] < 200:
                txn["desc_parts"].append(w["text"])
        nums.sort(key=lambda t: t[0])
        if len(nums) >= 2:
            txn["valor"] = _parse_amount(nums[0][1])
            txn["saldo"] = _parse_amount(nums[1][1])
        elif len(nums) == 1:
            txn["valor"] = _parse_amount(nums[0][1])
        txn["descripcion"] = " ".join(txn.pop("desc_parts"))
        txns.append(txn)

    return txns


def _id_cuenta_mercado_libre() -> int:
    fila = fetch_one(
        "SELECT IdCuentaBancaria FROM dbo.CuentasBancarias WHERE Banco = ? AND NumeroCuenta = ?",
        ("Mercado Libre", CVU_MERCADO_LIBRE),
    )
    if fila is None:
        raise ValueError(
            "No existe la cuenta Mercado Libre en CuentasBancarias — correr primero "
            "crear_tabla_movimientos_mercado_libre.py"
        )
    return fila["IdCuentaBancaria"]


def _existentes() -> set[tuple]:
    filas = fetch_all(
        "SELECT Fecha AS fecha, IdOperacion AS idOperacion, Importe AS importe, Saldo AS saldo "
        "FROM dbo.[Movimientos Mercado Libre]"
    )
    return {
        (
            f["fecha"].isoformat() if hasattr(f["fecha"], "isoformat") else f["fecha"],
            f["idOperacion"],
            round(float(f["importe"]), 2),
            round(float(f["saldo"]), 2) if f["saldo"] is not None else None,
        )
        for f in filas
    }


def _mapa_contactos() -> dict[str, int]:
    filas = fetch_all("SELECT IdContacto, [Razon Social] AS razon FROM dbo.Contactos")
    return {f["razon"].strip().lower(): f["IdContacto"] for f in filas if f["razon"]}


def _resolver_contacto(descripcion: str, contactos: dict[str, int]) -> int | None:
    exacto = contactos.get(descripcion.strip().lower())
    if exacto is not None:
        return exacto
    if "uatre" in descripcion.lower():
        return contactos.get("uatre")
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Escribe en WC (default: dry-run)")
    args = parser.parse_args()

    _assert_target_is_wc()

    archivos = sorted(glob.glob(CARPETA_RESUMENES))
    if not archivos:
        print(f"No se encontraron PDF en {CARPETA_RESUMENES}")
        return

    id_cuenta = _id_cuenta_mercado_libre()
    contactos = _mapa_contactos()
    existentes = _existentes()

    nuevos: list[dict] = []
    for path in archivos:
        for t in _parse_pdf(path):
            clave = (t["fecha"], t["id_operacion"], round(t["valor"], 2), round(t["saldo"], 2) if t["saldo"] is not None else None)
            if clave in existentes:
                continue
            existentes.add(clave)  # evita duplicar dentro de esta misma corrida
            nuevos.append(
                {
                    "fecha": t["fecha"],
                    "descripcion": t["descripcion"],
                    "idOperacion": t["id_operacion"],
                    "importe": t["valor"],
                    "saldo": t["saldo"],
                    "idContacto": _resolver_contacto(t["descripcion"], contactos),
                    "archivo": path,
                }
            )

    sin_contacto = sum(1 for n in nuevos if n["idContacto"] is None)
    print(f"{len(archivos)} PDF leídos. {len(nuevos)} movimientos nuevos ({sin_contacto} sin contacto resuelto).")
    for n in nuevos:
        print(f"  {n['fecha']} · {n['descripcion'][:60]:60s} · {n['importe']:>12,.2f} · saldo {n['saldo']}")

    if args.apply:
        statements = [
            (
                "INSERT INTO dbo.[Movimientos Mercado Libre] "
                "(Fecha, Descripcion, IdOperacion, Importe, Saldo, IdCuentaBancaria, IdContacto) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (n["fecha"], n["descripcion"], n["idOperacion"], n["importe"], n["saldo"], id_cuenta, n["idContacto"]),
            )
            for n in nuevos
        ]
        if statements:
            execute_write_transaction(statements)
        print(f"\nAplicados {len(nuevos)} movimientos nuevos.")
    else:
        print("\nDry-run: no se escribió nada. Correr con --apply para cargar (requiere backup de WC verificado).")


if __name__ == "__main__":
    main()
