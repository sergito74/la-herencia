"""Reprocesa un mail de sueldos de Outlook sin moverlo ni marcarlo. Simula salvo --aplicar.
Uso desde backend: python -m scripts.reprocesar_sueldos_mail ENTRY_ID [--aplicar]
"""
from __future__ import annotations

import argparse
from src.features.documentos_nuevos import mails, rutina
from src.features.documentos_nuevos.lectores import sueldos
from src.features.descarga_peajes.lectores import texto_pdf
from src.features.vinculos.backup import backup_verificado
from src.db.connection import reconciliation_transaction


def main(entry_id: str, aplicar=False):
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    try:
        ns = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        item = ns.GetItemFromID(entry_id)
        mail = mails.Mail(item.EntryID, mails._remitente(item), item.Subject or "",
                          item.ReceivedTime.replace(tzinfo=None), list(mails._adjuntos(item)))
    finally:
        pythoncom.CoUninitialize()
    reconocidos = []
    for adj in mail.adjuntos:
        if not adj.nombre.lower().endswith(".pdf"):
            continue
        texto = texto_pdf(adj.contenido)
        if not sueldos.reconoce(texto):
            continue
        reconocidos.append(adj)
        print(adj.nombre)
        if "Resumen de Sueldos" not in texto:
            for r in sueldos.empleados_y_existentes(sueldos.leer(adj.contenido)):
                print(r["empleado"], r["periodo"], r["neto"], "ya cargado" if r["existente"] else "para cargar")
    if not reconocidos:
        raise ValueError("El mail no tiene recibos o resumen de sueldos reconocidos de Giamigli")
    if not aplicar:
        print("Simulación: no se modificó el sistema.")
        return
    print("Respaldo verificado:", backup_verificado("sueldos-mail-octubre-20261029"))
    with reconciliation_transaction():
        for adj in reconocidos:
            print(adj.nombre, rutina.procesar_adjunto(None, mail, adj))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("entry_id")
    p.add_argument("--aplicar", action="store_true")
    a = p.parse_args()
    main(a.entry_id, a.aplicar)
