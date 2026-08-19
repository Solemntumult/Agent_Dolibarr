# 🤖 Dolibarr AI Agent — Assistant IA Interne pour ERP/CRM Dolibarr

[![Python](https://img.shields.io/badge/Python-3.10%2B%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask%203.1-green.svg)](https://flask.palletsprojects.com/)
[![OpenAI](https://img.shields.io/badge/LLM-OpenAI%20Function%20Calling-orange.svg)](https://platform.openai.com/)
[![Dolibarr](https://img.shields.io/badge/ERP%2FCRM-Dolibarr%20REST%20API-informational.svg)](https://www.dolibarr.org/)
[![Security](https://img.shields.io/badge/Security-Human--in--the--Loop%20%7C%20PromptGuard-red.svg)](#-sécurité-gouvernance-et-protection-des-données)

**Dolibarr AI Agent** est un assistant d'intelligence artificielle interne d'entreprise conçu pour **ICT Consulting** (conforme au *Cahier des Charges v1.0, Juillet 2026*). 

Il s'interface directement avec l'ERP/CRM **Dolibarr** via son API REST pour transformer des instructions en langage naturel en requêtes précises, automatiser les opérations récurrentes, assister la gestion commerciale et exécuter des tâches planifiées de manière hautement sécurisée et traçable.

---

## 📑 Sommaire

1. [Contexte et Enjeux Métier](#-contexte-et-enjeux-métier)
2. [Fonctionnalités Principales](#-fonctionnalités-principales)
3. [Architecture Technique](#-architecture-technique)
4. [Sécurité, Gouvernance et Protection des Données](#-sécurité-gouvernance-et-protection-des-données)
5. [Outils Exposés au Modèle (Function Calling)](#-outils-exposés-au-modèle-function-calling)
6. [Prérequis et Installation](#-prérequis-et-installation)
7. [Guide de Configuration (`.env`)](#-guide-de-configuration-env)
8. [Démarrage et Exploitation](#-démarrage-et-exploitation)
9. [Guide d'Utilisation](#-guide-dutilisation)
10. [Référence de l'API Interne](#-référence-de-lapi-interne)
11. [Tests et Recette](#-tests-et-recette)

---

## 🎯 Contexte et Enjeux Métier

### Le Constat
L'exploitation quotidienne d'un ERP/CRM comme Dolibarr nécessite de multiples clics, la navigation manuelle entre menus (tiers, devis, factures, stocks) et des tâches répétitives chronophages (relances de factures en retard, alertes de réapprovisionnement, consolidation de chiffres).

### Les Objectifs
* **Interrogation instantanée en langage naturel** : Obtenir en une phrase une synthèse commerciale, l'état d'un compte client ou la liste des impayés sans navigation complexe.
* **Accélération de la saisie** : Générer devis, factures et fiches clients à la volée depuis une simple consigne textuelle.
* **Automatisation intelligente** : Relances graduées des impayés (J+7, J+15, J+30), alertes automatiques de stock bas et rapports périodiques par e-mail.
* **Fiabilité et Contrôle total** : Éliminer le risque d'erreur humaine tout en conservant une validation systématique (*Human-in-the-loop*) avant toute écriture en base.

---

## 🌟 Fonctionnalités Principales

| Domaine | Description |
|---|---|
| 💬 **Interface Web de Conversation** | UI moderne (thème sombre épuré type DeepSeek), responsive (desktop/mobile), historique de sessions, cartes d'action interactives. |
| 🛡️ **Validation "Human-in-the-Loop"** | Toute action d'écriture génère une carte en attente d'approbation. Rien n'est écrit sans accord explicite de l'utilisateur. |
| 📄 **Génération & Téléchargement PDF** | Génération automatique des PDF officiels dans Dolibarr dès validation d'un devis ou d'une facture, avec téléchargement direct sécurisé. |
| 🧠 **RAG Vectoriel & Recherche Sémantique** | Indexation vectorielle locale via **FAISS** (`text-embedding-3-small`) pour une recherche rapide dans le catalogue et les documents. |
| ⏱️ **Ordonnanceur de Tâches (APScheduler)** | Routines autonomes configurables : relances impayés quotidiennes, vérification des stocks, rapports hebdomadaires. |
| ✉️ **Canal E-mail (IMAP / SMTP)** | Dépouillement automatisé des e-mails entrants autorisés, rédaction et expédition de réponses ou relances. |
| 📊 **Journal d'Audit & Traçabilité** | Enregistrement immuable de chaque intention, appel d'outil, paramètres, utilisateur et résultat dans la base locale. |

---

## 🏗️ Architecture Technique

Le projet repose sur le pattern architectural étendu **`terral_api`** (Route $\rightarrow$ Controller $\rightarrow$ Adaptater $\rightarrow$ Entity), enrichi d'une couche d'orchestration IA et de services spécialisés.

### Schéma Global de Fonctionnement

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                             UTILISATEUR INTERNE                             │
│                     (Interface Web Chat / Canal E-mail)                     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Requêtes HTTP / E-mails
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SERVEUR D'APPLICATION (VPS)                         │
│                                                                             │
│  ┌───────────────────────┐                    ┌──────────────────────────┐  │
│  │   Routes & Contrôleurs│                    │   Ordonnanceur de Tâches │  │
│  │   (Auth, Chat, Admin) │                    │    (APScheduler / Cron)  │  │
│  └───────────┬───────────┘                    └────────────┬─────────────┘  │
│              │                                             │                │
│              └──────────────────────┬──────────────────────┘                │
│                                     ▼                                       │
│                       ┌───────────────────────────┐                         │
│                       │   Orchestrateur d'Agent   │                         │
│                       │  (OpenAI Function Calling)│                         │
│                       └───────┬───────────┬───────┘                         │
│                               │           │                                 │
│               ┌───────────────┘           └──────────────┐                  │
│               ▼                                          ▼                  │
│  ┌──────────────────────────┐              ┌─────────────────────────────┐  │
│  │  Registre des Outils     │              │  PromptGuard & Sécurité     │  │
│  │  (Lecture / Écriture)    │              │  (Filtrage anti-injection)  │  │
│  └────────────┬─────────────┘              └─────────────────────────────┘  │
│               │                                                             │
│       ┌───────┴─────────────────────────────────┐                           │
│       ▼                                         ▼                           │
│  ┌──────────────────────────┐              ┌─────────────────────────────┐  │
│  │   Connecteur Dolibarr    │              │   Base Interne (SQLAlchemy) │  │
│  │   (Client API REST)      │              │   - Users & Sessions JWT    │  │
│  └────────────┬─────────────┘              │   - Conversations & Messages│  │
│               │                            │   - ToolExecutions & Audit  │  │
│               │                            │   - Tâches & Configuration  │  │
│               │                            └─────────────────────────────┘  │
└───────────────┼─────────────────────────────────────────────────────────────┘
                │                                           │
                ▼                                           ▼
┌────────────────────────────────┐         ┌──────────────────────────────────┐
│        INSTANCE DOLIBARR       │         │        FOURNISSEUR LLM           │
│           (ERP / CRM)          │         │     (OpenAI API Platform)        │
│   Tiers, Factures, Devis,      │         │   - Modèle Équilibré (gpt-4o)    │
│   Produits, Stocks, Agenda     │         │   - Modèle Léger / Embeddings    │
└────────────────────────────────┘         └──────────────────────────────────┘
```

### Organisation des Modules

```
dolibarr_ai_agent/
├── app/
│   ├── __init__.py            # Point d'entrée, initialisation Flask, DB, Seeder & Scheduler
│   ├── adaptater/             # Couche adaptateurs (Dolibarr REST, Auth, Audit, Conversation...)
│   │   └── dolibarr/          # Clients API Dolibarr (thirdparty, invoice, proposal, product...)
│   ├── agent/                 # Cœur de l'IA (orchestrator, tool_registry, confirmation)
│   │   └── tools/             # Définitions des outils exposés au LLM (read/write)
│   ├── commons/               # Configuration, instances partagées, helpers, erreurs, enums
│   ├── controllers/           # Logique métier et validation des requêtes
│   ├── core/                  # Dépendances applicatives et fabrique de l'application
│   ├── data/                  # Entités SQLAlchemy (User, Message, ToolExecution, AuditLog...)
│   ├── routes/                # Blueprints Flask (endpoints REST)
│   ├── seeder/                # Initialisation des données par défaut (admin, settings)
│   ├── services/              # Intégrations externes (OpenAI, SMTP/IMAP, RAG Vectoriel, Guard)
│   ├── static/ & templates/   # Interface utilisateur Web (HTML5/CSS3/Vanilla JS)
│   ├── uses_cases/            # Routines métier automatisées (relances, stocks, rapports)
│   └── wsgi.py                # Point d'entrée WSGI pour serveur de production (Gunicorn)
├── migrations/                # Scripts de migrations de schéma Alembic / Flask-Migrate
├── tests/                     # Tests automatisés et scripts de synchronisation E2E
├── requirements.txt           # Dépendances Python du projet
└── README.md                  # Documentation technique et opérationnelle
```

---

## 🔒 Sécurité, Gouvernance et Protection des Données

Le système applique une politique de sécurité stricte conforme aux exigences professionnelles et réglementaires (notamment les règles **APDP** de protection des données personnelles) :

### 1. Validation Obligatoire des Écritures (*Human-in-the-Loop*)
* Aucune écriture (création de client, émission de devis, génération de facture) n'est exécutée directement par l'agent.
* L'agent prépare l'action sous forme de `ToolExecution` en attente (`status: pending`).
* L'utilisateur valide ou refuse l'action directement dans l'interface de conversation.
* Les documents créés dans Dolibarr sont **systématiquement générés à l'état brouillon** (`status: 0`), laissant la validation comptable/commerciale finale aux personnes habilitées.

### 2. Protection Anti-Injection de Prompt (*PromptGuard*)
* Les contenus externes (corps d'e-mails, libellés importés) sont strictement isolés et traités comme des données passives et non des instructions système.
* Le service `PromptGuardService` analyse et neutralise les tentatives de contournement d'instructions ou d'exfiltration de contexte.

### 3. Moindre Privilège & Cloisonnement
* L'agent se connecte à Dolibarr via un utilisateur dédié muni d'une clé `DOLAPIKEY` limitée aux seuls modules nécessaires.
* L'accès à l'interface est protégé par des tokens **JWT révocables** avec vérification du statut utilisateur actif en base de données.
* Les secrets (`.env`) ne sont jamais commités dans le gestionnaire de versions.

### 4. Souveraineté et Confidentialité
* L'application, la base relationnelle et l'index vectoriel résident sur l'infrastructure de l'entreprise (VPS/Local).
* Seul le strict contexte textuel indispensable à la compréhension de la requête est transmis aux API du LLM.

---

## 🛠️ Outils Exposés au Modèle (Function Calling)

L'agent dispose d'un catalogue de fonctions formalisées selon le schéma JSON d'OpenAI :

### Outils de Consultation (Lecture seule)
* `search_client` / `get_client` : Recherche et consultation détaillée des fiches tiers.
* `list_unpaid_invoices` / `get_invoice` : Liste des factures impayées, retards et détails d'une facture.
* `list_products` / `get_stock_level` : Consultation du catalogue et des niveaux de stock réels.
* `list_quotes` : Consultation des propositions commerciales et statuts.
* `get_sales_statistics` : Calcul et agrégation du chiffre d'affaires et volumes de vente.

### Outils d'Action (Soumis à confirmation explicite)
* `create_client` : Création d'une nouvelle fiche client/prospect.
* `create_quote` : Génération d'un devis brouillon avec lignes de produits/services.
* `create_invoice` : Émission d'une facture client brouillon.
* `log_event` : Enregistrement d'un rendez-vous ou événement dans l'agenda commercial.

---

## ⚙️ Prérequis et Installation

### Prérequis Système
* **Python** : Version `3.10` ou supérieure (testé et compatible `3.13`).
* **Dolibarr** : Version `18.x` à `23.x` avec le module **API REST** activé.
* **Base de données** : SQLite (par défaut pour dév/test) ou PostgreSQL / MySQL.
* **Clé API OpenAI** : Avec accès aux modèles `gpt-4o` / `gpt-4o-mini` et `text-embedding-3-small`.

### Procédure d'Installation

```bash
# 1. Cloner ou extraire le projet
cd dolibarr_ai_agent_complet/dolibarr_ai_agent

# 2. Créer l'environnement virtuel Python
python -m venv .venv

# 3. Activer l'environnement virtuel
# Sur Windows (PowerShell) :
.venv\Scripts\Activate.ps1
# Sur Linux / macOS :
source .venv/bin/activate

# 4. Installer les dépendances
pip install -r requirements.txt
```

---

## 🔐 Guide de Configuration (`.env`)

Le fichier de configuration doit être placé dans :  
👉 `dolibarr_ai_agent/app/commons/const/const/.env`

```ini
# ===================================================================
# CONFIGURATION DE L'APPLICATION & SÉCURITÉ
# ===================================================================
SECRET_KEY=votre_cle_secrete_flask_tres_longue_et_aleatoire
JWT_SECRET_KEY=votre_cle_secrete_jwt_securisee
DATABASE_URL=sqlite:///agent.db
PORT=5000
FLASK_DEBUG=0

# ===================================================================
# COMPTE ADMINISTRATEUR INITIAL (Généré au 1er démarrage)
# ===================================================================
ADMIN_FULL_NAME=Administrateur ICT Consulting
ADMIN_EMAIL=admin@ictconsulting.bj
ADMIN_PASSWORD=SuperMotDePasseAChanger2026!

# ===================================================================
# CONNECTEUR DOLIBARR (API REST)
# ===================================================================
DOLAPIKEY=votre_cle_dolapikey_dolibarr
DOLIBARR_API_URL=http://localhost/dolibarr/api/index.php
DOLIBARR_TIMEOUT=30

# ===================================================================
# MOTEUR D'INTELLIGENCE ARTIFICIELLE (OPENAI)
# ===================================================================
OPENAI_API_KEY=sk-proj-votre_cle_openai_api
OPENAI_MODEL=gpt-4o-mini
OPENAI_MODEL_LIGHT=gpt-4o-mini
OPENAI_MODEL_BALANCED=gpt-4o-mini
OPENAI_MODEL_ADVANCED=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_MAX_ITERATIONS=8

# ===================================================================
# RAG VECTORIEL & OPTIMISATIONS DE CACHE
# ===================================================================
VECTOR_SEARCH_ENABLED=True
VECTOR_SYNC_ON_STARTUP=True
VECTOR_MIN_SCORE=0.72
QUERY_CACHE_ENABLED=True
QUERY_CACHE_TTL_SECONDS=300

# ===================================================================
# CANAL E-MAIL & NOTIFICATIONS (Optionnel)
# ===================================================================
IMAP_HOST=imap.votreserveur.com
IMAP_USER=agent@ictconsulting.bj
IMAP_PASSWORD=mot_de_passe_messagerie
IMAP_USE_SSL=True

SMTP_HOST=smtp.votreserveur.com
SMTP_USER=agent@ictconsulting.bj
SMTP_PASSWORD=mot_de_passe_messagerie
SMTP_USE_SSL=True
SMTP_FROM=agent@ictconsulting.bj

ALLOWED_EMAIL_SENDERS=direction@ictconsulting.bj,comptabilite@ictconsulting.bj
REPORT_RECIPIENTS=direction@ictconsulting.bj
```

---

## 🚀 Démarrage et Exploitation

### Démarrage en Mode Développement
```bash
python app/__init__.py
```
> Le serveur démarre par défaut sur `http://localhost:5000` (ou sur le port défini par la variable `PORT`).

### Démarrage en Production (Gunicorn / Linux VPS)
```bash
gunicorn --chdir app --workers 3 --bind 0.0.0.0:5000 wsgi:app
```

### Initialisation Automatique au 1er Lancement
Lors du premier démarrage, l'application exécute automatiquement :
1. La création des tables dans la base de données relationnelle.
2. L'application des migrations Alembic.
3. Le seeder créant le compte **Administrateur** et les configurations d'alertes par défaut.
4. La synchronisation initiale de l'index vectoriel FAISS.
5. Le démarrage des jobs planifiés de l'ordonnanceur.

---

## 💡 Guide d'Utilisation

### 1. Accès à l'Application
1. Rendez-vous sur `http://localhost:5000` dans votre navigateur.
2. Connectez-vous avec l'adresse e-mail et le mot de passe administrateur configurés dans votre fichier `.env`.

### 2. Exemples d'Interactions en Langage Naturel

* **Consultation Commerciale :**
  > « *Quel est le chiffre d'affaires réalisé ce mois-ci ?* »  
  > « *Quels sont les clients qui n'ont passé aucune commande depuis 3 mois ?* »

* **Gestion des Impayés :**
  > « *Donne-moi la liste de toutes les factures en retard de paiement de plus de 15 jours avec les montants.* »

* **Création de Devis / Facture :**
  > « *Crée un devis pour le client RENOV SOLUTIONS : 5 jours d'assistance technique à 200 000 FCFA par jour.* »  
  > ↳ *L'agent affiche un aperçu détaillé du devis avec deux boutons : **[Confirmer l'action]** et **[Refuser]**.*

* **Téléchargement du Document :**
  > Dès confirmation, le devis est créé sous Dolibarr, son PDF officiel est compilé et un bouton **[Télécharger le PDF]** apparaît instantanément dans la discussion.

---

## 🔌 Référence de l'API Interne

| Méthode | Endpoint | Description | Niveau d'accès |
|---|---|---|---|
| `POST` | `/api/auth/login` | Authentification utilisateur & émission du token JWT | Public |
| `GET` | `/api/auth/me` | Récupération du profil de l'utilisateur connecté | Utilisateur connecté |
| `POST` | `/api/auth/logout` | Révocation de session et déconnexion | Utilisateur connecté |
| `POST` | `/api/chat/` | Envoi d'un message à l'agent IA (boucle de raisonnement) | Utilisateur connecté |
| `GET` | `/api/chat/conversations` | Liste des conversations de l'utilisateur | Utilisateur connecté |
| `POST` | `/api/chat/conversations` | Initialisation d'une nouvelle session de conversation | Utilisateur connecté |
| `GET` | `/api/chat/conversations/<id>/messages` | Récupération de l'historique complet des messages | Utilisateur connecté |
| `GET` | `/api/confirmation/pending` | Liste des actions en attente d'approbation | Utilisateur connecté |
| `POST` | `/api/confirmation/<id>/confirm` | **Validation et exécution** de l'action dans Dolibarr | Utilisateur connecté |
| `POST` | `/api/confirmation/<id>/reject` | Refus et annulation de l'action | Utilisateur connecté |
| `GET` | `/api/confirmation/<id>/document` | Téléchargement sécurisé du PDF officiel Dolibarr | Auteur ou Admin |
| `GET` | `/api/admin/agent_config/settings` | Consultation des paramètres de l'agent et des seuils | Administrateur |
| `PUT` | `/api/admin/agent_config/settings` | Mise à jour dynamique de la configuration | Administrateur |
| `GET` | `/api/admin/agent_config/audit` | Consultation du journal d'audit complet | Administrateur |
| `POST` | `/api/admin/agent_config/tasks/<id>/run` | Déclenchement manuel immédiat d'une tâche planifiée | Administrateur |

---

## 🧪 Tests et Recette

Le projet inclut une suite de tests de validation d'intégration de bout en bout avec Dolibarr :

```bash
# Exécution du test de synchronisation et de cycle de vie complet
python tests/test_e2e_dolibarr_sync.py
```

Ce test vérifie :
- La connectivité avec l'API REST Dolibarr.
- La récupération des tiers, factures, devis et produits.
- La création sécurisée de documents brouillons avec simulation de confirmation.
- La génération et l'intégrité du document PDF retourné.

---

## 📄 Licence et Propriété

Projet développé pour **ICT Consulting**. Tous droits réservés (2026).
