"""Cifrado de la bóveda (042, T009)."""

from __future__ import annotations

import pytest
from cryptography.exceptions import InvalidTag

from src.features.boveda import cifrado


def test_ida_y_vuelta(keyring_falso):
    blob = cifrado.cifrar("s3creto-ñ", cifrado.aad_clave(7))
    assert b"s3creto" not in blob
    assert cifrado.descifrar(blob, cifrado.aad_clave(7)).valor() == "s3creto-ñ"


def test_aad_distinta_no_descifra(keyring_falso):
    blob = cifrado.cifrar("s3creto", cifrado.aad_clave(7))
    with pytest.raises(InvalidTag):
        cifrado.descifrar(blob, cifrado.aad_clave(8))
    with pytest.raises(InvalidTag):
        cifrado.descifrar(blob, cifrado.aad_dato(7, "PIN"))


def test_otra_clave_maestra_no_descifra(keyring_falso):
    blob = cifrado.cifrar("s3creto", cifrado.aad_clave(1))
    keyring_falso.valores.clear()
    cifrado.clave_maestra(crear=True)
    with pytest.raises(InvalidTag):
        cifrado.descifrar(blob, cifrado.aad_clave(1))


def test_sin_clave_maestra_no_crea_en_silencio(keyring_falso):
    keyring_falso.valores.clear()
    with pytest.raises(cifrado.ClaveMaestraNoDisponible):
        cifrado.descifrar(b"x" * 40, cifrado.aad_clave(1))
    with pytest.raises(cifrado.ClaveMaestraNoDisponible):
        cifrado.cifrar("s", cifrado.aad_clave(1))
    assert keyring_falso.valores == {}


def test_no_crea_otra_clave_si_ya_hay_secretos(keyring_falso, monkeypatch):
    from src.features.boveda import repository

    keyring_falso.valores.clear()
    monkeypatch.setattr(repository, "hay_secretos", lambda: True)
    with pytest.raises(cifrado.ClaveMaestraNoDisponible):
        repository.clave_para_escribir()
    assert keyring_falso.valores == {}
    monkeypatch.setattr(repository, "hay_secretos", lambda: False)
    assert len(repository.clave_para_escribir()) == 32


def test_secreto_no_se_imprime():
    s = cifrado.Secreto("s3creto")
    assert "s3creto" not in repr(s)
    assert "s3creto" not in str(s)
    assert "s3creto" not in f"{s}"
    assert "s3creto" not in repr([s])
