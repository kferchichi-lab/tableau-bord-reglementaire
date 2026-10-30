"""Comptes utilisateurs (profils Responsable / Admin).

Les empreintes (hash PBKDF2) peuvent — et devraient — être fournies par ``st.secrets`` :

    [auth]
    admin_hash = "sel$empreinte"
    [auth.responsables]
    SABER = "sel$empreinte"

Les valeurs ci-dessous ne servent que de repli si ``secrets.toml`` ne les définit pas.
Pour générer une empreinte :  ``python -m tpr.core.hash_cli``.
"""

from __future__ import annotations

from copy import deepcopy

import streamlit as st

ADMIN_HASH_DEFAUT = "69d097edbe715222649bfc7296f14331$ed69ae3c1298c0254a053fa6650745b588637332095855e2541c1aeb784fff98"

COMPTES_RESPONSABLES_DEFAUT: dict[str, dict] = {
    "SABER": {
        "hash": "df08cf138fa54315e428e454a2bfcd91$2a12dbc095764565b0fe5682001a39eb738dc01c1b8c4fbedead2a9d170b3a13",
        "nom": "Saber BEN CHAABEN", "entites": ["Maintenance"], "site": "MEG",
    },
    "HSE": {
        "hash": "316b35609d01dcc04bd1cc0610bc6768$a3835ace3975737dcda29c8c83ff6e7cbab3a223a40ec464ea4d6dfd4cf01da1",
        "nom": "Montassar MEHRABI", "entites": ["HSE"], "site": None,
    },
    "AICHA": {
        "hash": "4c990dd6d323e5c52ed2175e4ebc9580$5bc468e84a0d1323ee52a1d6b1e0281d27c9ddf184b417290fceeacc10ba6a99",
        "nom": "Aïcha BELLAKHAL", "entites": ["BT", "Chef service BT", "RH", "DG"], "site": None,
    },
    "CHAFIK": {
        "hash": "a69216e51a745c746dce04d1d9a9ea3f$9263b18f3fdfb31fabd1a912dc8009fe054b2e0b1818e2c1f090ca07494f150f",
        "nom": "Chafik ABID", "entites": ["Maintenance"], "site": "SGB",
    },
}


def charger_comptes() -> tuple[str, dict[str, dict]]:
    """Retourne ``(hash_admin, comptes_responsables)`` en appliquant la surcharge de ``st.secrets``."""
    admin_hash = ADMIN_HASH_DEFAUT
    comptes = deepcopy(COMPTES_RESPONSABLES_DEFAUT)
    try:
        admin_hash = st.secrets["auth"]["admin_hash"]
    except Exception:
        pass
    try:
        for identifiant, empreinte in st.secrets["auth"]["responsables"].items():
            if identifiant in comptes:
                comptes[identifiant]["hash"] = empreinte
    except Exception:
        pass
    return admin_hash, comptes
