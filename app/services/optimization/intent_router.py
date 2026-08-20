"""Sélection dynamique des outils exposés au LLM selon l'intention utilisateur."""
import re

from commons.enums.tool_sense.tool_sense import ToolSense

# Outils toujours disponibles en lecture de base
_BASE_READ = {"search_client", "get_client"}

# Mapping mots-clés → outils
_INTENT_MAP = [
    (r"\b(chiffre|ca\b|affaires|ventes|revenu|facturé|facture.{0,12}mois|trimestre|semestre|année)\b",
     {"get_sales_statistics"}),
    (r"\b(impay|retard|échu|echu|recouvr|créance|creance|relance)\b",
     {"list_unpaid_invoices", "get_invoice"}),
    (r"\b(envoie|envoyer|télécharg|telecharg|pdf|document|fichier|donne-moi|récupérer|recuperer|telecharger)\b",
     {"get_document", "get_invoice", "get_quote"}),
    (r"\b(transform|convert|passer en facture|facturer|devis en facture)\b",
     {"convert_quote_to_invoice", "get_quote", "list_quotes", "create_invoice"}),
    (r"\b(facture|invoice)\b",
     {"list_unpaid_invoices", "get_invoice", "get_document"}),
    (r"\b(devis|proposition|quote|propal)\b",
     {"list_quotes", "get_quote", "get_document", "search_client"}),
    (r"\b(stock|seuil|rupture|inventaire|produit.{0,12}bas)\b",
     {"get_stock_level", "list_products"}),
    (r"\b(produit|catalogue|article|service|référence|ref\b)\b",
     {"list_products", "get_stock_level"}),
    (r"\b(client|tiers|fournisseur|coordonnées|coordonnees)\b",
     {"search_client", "get_client"}),
    (r"\b(créer|creer|nouveau|nouvelle|ajouter|générer|generer|faire un devis|faire une facture|transformer|convertir)\b",
     {"create_client", "create_quote", "create_invoice", "convert_quote_to_invoice", "log_event"}),
    (r"\b(agenda|événement|evenement|rdv|rendez|planifier|calendrier)\b",
     {"log_event"}),
]

_WRITE_TOOLS = {"create_client", "create_quote", "create_invoice", "convert_quote_to_invoice", "log_event"}


class IntentRouter:

    @staticmethod
    def select_tool_names(message: str, include_write: bool = True, last_assistant_message: str = None) -> set:
        text = (message or "").strip().lower()
        selected = set(_BASE_READ)

        # Détection des réponses courtes contextuelles
        is_short_reply = len(text) <= 30 or re.search(
            r"^(non|oui|vas-y|vas y|ok|d'accord|daccord|confirme|valide|crée|cree|procède|procede|fais-le|fais le|go|c'est bon|c est bon|aucun|aucune)\b",
            text,
            re.IGNORECASE,
        )

        last_text = (last_assistant_message or "").lower()
        has_writing_context = any(w in last_text for w in ["facture", "devis", "client", "récapitulatif", "créer", "finaliser", "souhaitez-vous", "confirmation"])

        # Réponse courte + contexte d'écriture : n'exposer que les outils d'écriture
        # (pas besoin de search_client, list_products, etc. pour un simple "oui")
        if is_short_reply and has_writing_context and include_write:
            return _WRITE_TOOLS | {"search_client"}

        for pattern, tools in _INTENT_MAP:
            if re.search(pattern, text, re.IGNORECASE):
                selected.update(tools)

        if include_write and (is_short_reply or has_writing_context):
            selected.update(_WRITE_TOOLS)

        if not include_write:
            selected -= _WRITE_TOOLS

        # Question générale sans mot-clé : outils de lecture principaux
        if len(selected) <= len(_BASE_READ):
            selected.update({
                "get_sales_statistics",
                "list_unpaid_invoices",
                "list_products",
                "get_stock_level",
                "list_quotes",
            })

        return selected

    @staticmethod
    def filter_definitions(all_definitions: list, selected_names: set) -> list:
        if not selected_names:
            return all_definitions
        return [
            d for d in all_definitions
            if d.get("function", {}).get("name") in selected_names
        ]

    @staticmethod
    def get_status_label(message: str) -> str:
        """Libellé affiché côté UI pendant le traitement."""
        text = (message or "").lower()
        checks = [
            (r"\b(chiffre|ca\b|affaires|trimestre)\b", "Calcul du chiffre d'affaires…"),
            (r"\b(impay|retard)\b", "Consultation des factures impayées…"),
            (r"\b(stock|rupture)\b", "Analyse des niveaux de stock…"),
            (r"\b(devis)\b", "Recherche des devis…"),
            (r"\b(créer|creer|nouveau|nouvelle)\b", "Préparation d'une action…"),
            (r"\b(client|tiers)\b", "Recherche client…"),
            (r"\b(produit|catalogue)\b", "Consultation du catalogue…"),
        ]
        for pattern, label in checks:
            if re.search(pattern, text, re.IGNORECASE):
                return label
        return "Analyse de votre demande…"
