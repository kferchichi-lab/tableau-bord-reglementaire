# Tableau de Bord Réglementaire — TPR

Application Streamlit de suivi du contrôle réglementaire (sites MEG et SGB) : rapports CR, planification,
exigences, KPI, suivi des actions, avec profils Visiteur / Responsable / Admin et Google Sheets comme base.

## Lancer
    pip install -r requirements.txt
    streamlit run app.py
Placez `unnamed.png` et `Cartographie.png` à la racine (optionnels). Copiez `.streamlit/secrets.toml.example`
vers `.streamlit/secrets.toml` et renseignez-le. Tests : `pytest`. Lint : `ruff check .`

## Architecture
| Dossier | Rôle |
|---|---|
| `app.py` | Point d'entrée : configuration, authentification, routage des onglets |
| `tpr/config.py` | Constantes métier (sites, périodicités, couleurs, identifiants de classeurs) |
| `tpr/context.py` | `AppContext` : profil, droits et données partagés par les vues |
| `tpr/core/` | Sécurité (PBKDF2, anti-bruteforce), comptes, état de session |
| `tpr/services/` | Google (auth, Sheets, codification), dépôt de données, e-mail, audit |
| `tpr/domain/` | Règles métier (calendrier, pilotes) |
| `tpr/reports/` | Générateurs PDF / Excel |
| `tpr/ui/` | En-tête, barre latérale, connexion OTP, indicateurs, thème (`css/`) |
| `tpr/views/` | Un module par onglet, chacun expose `render(ctx)` |
