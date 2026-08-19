import os
from commons.helpers.load_doten import load_env

load_env()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Dolibarr (API REST) ---
    DOLAPIKEY = os.getenv("DOLAPIKEY")
    DOLIBARR_API_URL = os.getenv("DOLIBARR_API_URL")
    DOLIBARR_TIMEOUT = int(os.getenv("DOLIBARR_TIMEOUT", "30"))

    # --- OpenAI ---
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    # Modèle par défaut fourni par l'utilisateur (cahier des charges §4.2 : choix paramétrable)
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    # Paliers de modèles : tâches répétitives (light), conversation (balanced), analyses (advanced)
    OPENAI_MODEL_LIGHT = os.getenv("OPENAI_MODEL_LIGHT", OPENAI_MODEL)
    OPENAI_MODEL_BALANCED = os.getenv("OPENAI_MODEL_BALANCED", OPENAI_MODEL)
    OPENAI_MODEL_ADVANCED = os.getenv("OPENAI_MODEL_ADVANCED", OPENAI_MODEL)
    OPENAI_MAX_ITERATIONS = int(os.getenv("OPENAI_MAX_ITERATIONS", "8"))
    OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    # --- Optimisation tokens / recherche vectorielle ---
    VECTOR_SEARCH_ENABLED = os.getenv("VECTOR_SEARCH_ENABLED", "True").lower() in ("true", "1", "yes")
    VECTOR_SYNC_ON_STARTUP = os.getenv("VECTOR_SYNC_ON_STARTUP", "True").lower() in ("true", "1", "yes")
    VECTOR_MIN_SCORE = float(os.getenv("VECTOR_MIN_SCORE", "0.72"))
    LLM_HISTORY_LIMIT = int(os.getenv("LLM_HISTORY_LIMIT", "6"))
    LLM_MESSAGE_MAX_CHARS = int(os.getenv("LLM_MESSAGE_MAX_CHARS", "1500"))
    LLM_TOOL_RESULT_MAX_ITEMS = int(os.getenv("LLM_TOOL_RESULT_MAX_ITEMS", "15"))
    QUERY_CACHE_ENABLED = os.getenv("QUERY_CACHE_ENABLED", "True").lower() in ("true", "1", "yes")
    QUERY_CACHE_TTL_SECONDS = int(os.getenv("QUERY_CACHE_TTL_SECONDS", "300"))
    LLM_TITLE_GENERATION = os.getenv("LLM_TITLE_GENERATION", "False").lower() in ("true", "1", "yes")

    # --- E-mail (cahier des charges §4.5 : canal e-mail entrant/sortant) ---
    IMAP_HOST = os.getenv("IMAP_HOST")
    IMAP_USER = os.getenv("IMAP_USER")
    IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")
    IMAP_USE_SSL = os.getenv("IMAP_USE_SSL", "True").lower() in ("true", "1", "yes")

    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "True").lower() in ("true", "1", "yes")
    SMTP_FROM = os.getenv("SMTP_FROM") or os.getenv("SMTP_USER") or "agent@ictconsulting.bj"

    # Expéditeurs autorisés à solliciter l'agent par e-mail (séparés par des virgules) — §4.5/§5.1
    ALLOWED_EMAIL_SENDERS = [
        s.strip().lower() for s in os.getenv("ALLOWED_EMAIL_SENDERS", "").split(",") if s.strip()
    ]
    # Destinataires des rapports périodiques et alertes de stock (séparés par des virgules)
    REPORT_RECIPIENTS = [
        r.strip() for r in os.getenv("REPORT_RECIPIENTS", "").split(",") if r.strip()
    ]

    # --- Compte administrateur interne initial (créé par le seeder au premier démarrage) ---
    ADMIN_FULL_NAME = os.getenv("ADMIN_FULL_NAME", "Administrateur ICT Consulting")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
