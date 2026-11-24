"""Pasa por el lector de LPG los avisos de Ventas de granos que quedaron «para cargar» y los certificados de IVA de
granos pendientes (24/11/2026). Re-corrible: lo ya cargado se reconoce por el COE / número de certificado.
Uso (desde backend/): python -m scripts.cargar_lpg_pendientes [--aplicar]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.connection import execute_write, fetch_all  # noqa: E402
from src.features.ventas_granos import lector_lpg  # noqa: E402

ESTADO = {"cargado_auto": "cargado_solo", "ya_cargado": "ya_estaba", "pendiente": "para_cargar"}


def _actualizar(d: dict, r: dict, modulo: str) -> None:
    execute_write("UPDATE dbo.DocumentosNuevos SET Estado = ?, Modulo = ?, IdRegistro = ?, Motivo = ? WHERE IdDocumentoNuevo = ?",
                  (ESTADO[r["estadoCarga"]], modulo, r.get("idRegistro"), (r.get("motivo") or "")[:300] or None, d["id"]))
    if d.get("idPortalDoc"):
        execute_write("UPDATE dbo.Portales_Documentos SET EstadoCarga = ?, Motivo = ? WHERE IdDocumento = ?",
                      (r["estadoCarga"], (r.get("motivo") or "")[:300] or None, d["idPortalDoc"]))


def main():
    aplicar = "--aplicar" in sys.argv
    liqs = fetch_all("SELECT IdDocumentoNuevo AS id, IdDocumentoPortal AS idPortalDoc, Ruta AS ruta, IdContacto AS c "
                     "FROM dbo.DocumentosNuevos WHERE Modulo = 'granos' AND Tipo = 'liquidacion' AND Estado = 'para_cargar'")
    for d in liqs:
        pdf = Path(d["ruta"]).read_bytes()
        r = lector_lpg.cargar_lpg(pdf, d["ruta"], id_contacto=d["c"], simular=not aplicar)
        print(f"Liquidación aviso {d['id']}: {r['estadoCarga']} venta {r.get('idRegistro')} — {r.get('motivo')}")
        if aplicar:
            _actualizar(d, r, "granos")
    certs = fetch_all("SELECT IdDocumentoNuevo AS id, IdDocumentoPortal AS idPortalDoc, Ruta AS ruta, Modulo AS m "
                      "FROM dbo.DocumentosNuevos WHERE Tipo = 'retencion' AND Estado = 'para_cargar'")
    for d in certs:
        pdf = Path(d["ruta"]).read_bytes()
        if not lector_lpg.leer_certificado(lector_lpg._texto(pdf)):
            continue
        if not aplicar:
            print(f"Certificado aviso {d['id']}: se asociaría a su liquidación")
            continue
        r = lector_lpg.aplicar_certificado(pdf, d["ruta"])
        print(f"Certificado aviso {d['id']}: {r['estadoCarga']} venta {r.get('idRegistro')} — {r.get('motivo')}")
        _actualizar(d, r, "granos" if r.get("idRegistro") else d["m"])


if __name__ == "__main__":
    main()
