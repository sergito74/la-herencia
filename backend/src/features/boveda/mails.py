"""Código de ingreso que un portal manda por mail, leído de Outlook (042). Solo lectura: no marca, mueve ni borra."""

from __future__ import annotations

import re
import time
from datetime import datetime, timedelta

from src.features.boveda.conectores import RequiereIntervencion


def esperar_codigo(remitente: str, patron: str, desde: datetime, espera_segundos: int = 180) -> str:
    """Primer grupo de `patron` (en asunto y cuerpo) del mail de `remitente` recibido después de `desde` (hora
    local; pywin32 entrega la hora local de Outlook rotulada UTC)."""
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    try:
        ns = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        regex = re.compile(patron)
        limite = time.monotonic() + espera_segundos
        desde = desde - timedelta(seconds=30)  # tolerancia de reloj
        while time.monotonic() < limite:
            ns.SendAndReceive(False)  # Gmail en Outlook sincroniza cada varios minutos: se fuerza la descarga
            time.sleep(10)
            for store in ns.Stores:
                try:
                    items = store.GetDefaultFolder(6).Items  # 6 = Bandeja de entrada
                    items.Sort("[ReceivedTime]", True)
                except Exception:
                    continue
                for i, m in enumerate(items):
                    if i >= 20:
                        break
                    try:
                        if m.ReceivedTime.replace(tzinfo=None) < desde:
                            break
                        if (m.SenderEmailAddress or "").lower() != remitente.lower():
                            continue
                        encontrado = regex.search(f"{m.Subject}\n{m.Body}")
                        if encontrado:
                            return encontrado.group(1)
                    except Exception:
                        continue
        raise RequiereIntervencion(f"no llegó el mail con el código de {remitente}")
    finally:
        pythoncom.CoUninitialize()
