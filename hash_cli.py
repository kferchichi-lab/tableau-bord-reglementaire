"""Utilitaire : génère une empreinte de mot de passe à coller dans ``secrets.toml``.

Usage :  python -m tpr.core.hash_cli
"""

from __future__ import annotations

import getpass

from tpr.core.security import hacher_mot_de_passe


def main() -> None:
    mot_de_passe = getpass.getpass("Mot de passe à hacher : ")
    print(hacher_mot_de_passe(mot_de_passe))


if __name__ == "__main__":
    main()
