# Dolibarr AI Agent

Assistant IA interne pour l'ERP/CRM Dolibarr, dévelopé pour ICT Consulting.

## Fonctionnalités

- Interrogation en langage naturel (chiffre d'affaires, impayés, stocks, clients)
- Génération de devis et factures à l'état brouillon
- Automatisation des relances et alertes
- Validation humaine obligatoire avant toute écriture

## Installation

```bash
cd dolibarr_ai_agent
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

## Configuration

Créer le fichier `.env` dans `app/commons/const/const/` avec les variables nécessaires (voir `.env.example`).

## Démarrage

```bash
python app/__init__.py
```

L'interface est accessible sur `http://localhost:5000`.

## Production

```bash
gunicorn --chdir app --workers 3 --bind 0.0.0.0:5000 wsgi:app
```
