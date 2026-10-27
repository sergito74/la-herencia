"""Mails nuevos de Outlook para la rutina (043, research R2). Solo lectura: no marca, mueve, responde ni borra.

Recorre la bandeja de entrada de cada almacén (Outlook, La Herencia, Alquileres, …) y entrega los mails con
`ReceivedTime` posterior a la marca de ese almacén, con sus adjuntos PDF/XML. La marca la adelanta la rutina
cuando terminó de procesar el almacén (`Rutina_MarcaMails`). Sin marca previa (primera corrida) se fija en
ahora y no se barre la historia.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterator

EXTENSIONES = (".pdf", ".xml")
BANDEJA_ENTRADA = 6
MAXIMO_POR_ALMACEN = 500


@dataclass
class Adjunto:
    nombre: str
    contenido: bytes


@dataclass
class Mail:
    entry_id: str
    remitente: str
    asunto: str
    recibido: datetime
    adjuntos: list[Adjunto] = field(default_factory=list)


@dataclass
class Almacen:
    nombre: str
    marca: datetime | None
    mails: list[Mail]
    ultimo: datetime | None  # ReceivedTime más nuevo visto: nueva marca si el almacén se procesa bien


def nuevos(marca_de: Callable[[str], datetime | None], ahora: datetime | None = None) -> Iterator[Almacen | Exception]:
    """Un `Almacen` por almacén de Outlook. Si un almacén no se puede leer, entrega la excepción en su lugar
    (la rutina lo informa y no adelanta su marca). Si Outlook no responde, la excepción sale de acá."""
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    try:
        ns = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        vistos: set[str] = set()
        for store in ns.Stores:
            clave = f"{getattr(store, 'DisplayName', '')}|{getattr(store, 'FilePath', '')}"
            if clave in vistos:  # Outlook puede listar dos veces el mismo .pst
                continue
            vistos.add(clave)
            try:
                yield _leer_almacen(store, marca_de, ahora or datetime.now())
            except Exception as e:  # almacén sin bandeja (archivos PST) o desconectado
                e.almacen = getattr(store, "DisplayName", "?")
                yield e
    finally:
        pythoncom.CoUninitialize()


def _leer_almacen(store, marca_de, ahora: datetime) -> Almacen:
    nombre = store.DisplayName
    marca = marca_de(nombre)
    if marca is None:  # primera corrida: desde ahora, sin barrer historia
        return Almacen(nombre, None, [], ahora)
    items = store.GetDefaultFolder(BANDEJA_ENTRADA).Items
    items.Sort("[ReceivedTime]", True)
    mails, ultimo = [], marca
    for i, m in enumerate(items):
        if i >= MAXIMO_POR_ALMACEN:
            break
        try:
            recibido = m.ReceivedTime.replace(tzinfo=None)  # pywin32 rotula UTC la hora local de Outlook
        except Exception:
            continue  # no es un mail (invitación, aviso de lectura)
        if recibido <= marca:
            break
        ultimo = max(ultimo, recibido)
        adjuntos = list(_adjuntos(m))
        if adjuntos:
            mails.append(Mail(m.EntryID, _remitente(m), m.Subject or "", recibido, adjuntos))
    return Almacen(nombre, marca, mails, ultimo)


def _remitente(m) -> str:
    try:
        return m.SenderName or m.SenderEmailAddress or ""
    except Exception:
        return ""


def _adjuntos(m) -> Iterator[Adjunto]:
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(1, m.Attachments.Count + 1):
            a = m.Attachments.Item(i)
            nombre = a.FileName or ""
            if not nombre.lower().endswith(EXTENSIONES):
                continue
            ruta = Path(tmp) / f"{i}_{Path(nombre).name}"
            a.SaveAsFile(str(ruta))
            yield Adjunto(nombre, ruta.read_bytes())
