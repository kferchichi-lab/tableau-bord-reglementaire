"""Test de fumée : l'application démarre et affiche l'écran de connexion / les onglets."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from streamlit.testing.v1 import AppTest

from tpr.core.security import hacher_mot_de_passe, verifier_mot_de_passe


def test_hash_roundtrip():
    h = hacher_mot_de_passe("secret")
    assert verifier_mot_de_passe("secret", h) and not verifier_mot_de_passe("autre", h)


def test_login_visiteur():
    at = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=60).run()
    assert not at.exception, at.exception
    assert any("Adresse e-mail" in m.value for m in at.markdown)


def test_admin_voit_les_onglets():
    at = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=60)
    at.secrets["auth"] = {"admin_hash": hacher_mot_de_passe("pw-test")}
    at.run()
    at.selectbox[0].select("Admin").run()
    at.text_input[0].set_value("pw-test").run()
    assert not at.exception, at.exception
    assert len(at.tabs) == 6


def test_responsable_voit_suivi_actions():
    at = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=60)
    at.secrets["auth"] = {"responsables": {"HSE": hacher_mot_de_passe("pw-hse")}}
    at.run()
    at.selectbox[0].select("Responsable").run()
    at.text_input[0].set_value("hse").run()
    at.text_input[1].set_value("pw-hse").run()
    assert not at.exception, at.exception
    assert len(at.tabs) == 5
