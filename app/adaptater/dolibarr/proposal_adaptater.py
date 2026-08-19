"""Adaptateur propositions commerciales (devis) — lecture et création via l'API REST Dolibarr.

Points d'accès (cahier des charges §4.3) : /proposals, /proposals/{id}.
Statuts Dolibarr (fk_statut) : 0 brouillon, 1 validée (en attente de validation client),
2 signée/acceptée, 3 non acceptée, 4 envoyée.
"""
from datetime import datetime, timezone

from adaptater.dolibarr.dolibarr_client_adaptater import DolibarrClientAdaptater, DolibarrClientError
from commons.instances.instances import logger
from data.schemas.proposal_schema import ProposalSchema


class ProposalAdaptater:

    @staticmethod
    def list_proposals(status: str = "pending", limit: int = 100) -> list:
        """Liste les devis. status: 'pending' (en attente de validation client, statut 1) | 'all'."""
        try:
            params = {"limit": min(int(limit) or 100, 500), "sortfield": "t.datep", "sortorder": "DESC"}
            if status == "pending":
                params["sqlfilters"] = "(t.fk_statut:=:1)"
            raw_list = DolibarrClientAdaptater.get("proposals", params=params)
            result = [ProposalSchema(raw).to_dict() for raw in raw_list if isinstance(raw, dict)]

            # L'API devis ne renvoie que le socid : on enrichit avec le nom du client
            # via une requête groupée sur les tiers (opérateur :in:).
            socids = {int(p["client_id"]) for p in result if p.get("client_id")}
            if socids:
                try:
                    batch = DolibarrClientAdaptater.get("thirdparties", params={
                        "limit": min(len(socids), 100),
                        "sortfield": "t.rowid",
                        "sqlfilters": f"(t.rowid:in:{','.join(str(s) for s in sorted(socids))})",
                    })
                    names = {int(t.get("id")): t.get("name") for t in batch if isinstance(t, dict)}
                    for p in result:
                        if not p.get("client_name") and p.get("client_id"):
                            p["client_name"] = names.get(int(p["client_id"])) or p["client_name"]
                except DolibarrClientError as e:
                    logger.warning(f"ProposalAdaptater: enrichissement noms clients ignoré: {e}")
            return result
        except DolibarrClientError as e:
            logger.error(f"ProposalAdaptater.list_proposals failed: {e}")
            raise e

    @staticmethod
    def get_by_id(proposal_id: int) -> dict:
        try:
            raw = DolibarrClientAdaptater.get(f"proposals/{int(proposal_id)}")
            return ProposalSchema(raw).to_dict()
        except DolibarrClientError as e:
            logger.error(f"ProposalAdaptater.get_by_id({proposal_id}) failed: {e}")
            raise e

    @staticmethod
    def get_by_ref(ref: str) -> dict:
        try:
            import re
            prov_match = re.search(r"PROV(\d+)", ref, re.IGNORECASE)
            if prov_match:
                try:
                    return ProposalAdaptater.get_by_id(int(prov_match.group(1)))
                except DolibarrClientError:
                    pass

            clean_ref = ref.replace("(", "").replace(")", "").strip()
            raw_list = DolibarrClientAdaptater.get("proposals", params={"sqlfilters": f"(t.ref:=:'{clean_ref}')"})
            if raw_list and isinstance(raw_list, list) and len(raw_list) > 0 and isinstance(raw_list[0], dict):
                return ProposalAdaptater.get_by_id(int(raw_list[0]["id"]))
            raise DolibarrClientError(f"Devis introuvable pour la référence {ref}.")
        except DolibarrClientError as e:
            logger.error(f"ProposalAdaptater.get_by_ref({ref}) failed: {e}")
            raise e

    @staticmethod
    def get_by_id_or_ref(identifier) -> dict:
        """Récupère un devis soit par son ID numérique soit par sa référence."""
        import re
        str_val = str(identifier).strip()
        if str_val.isdigit():
            return ProposalAdaptater.get_by_id(int(str_val))
        prov_match = re.search(r"PROV(\d+)", str_val, re.IGNORECASE)
        if prov_match:
            try:
                return ProposalAdaptater.get_by_id(int(prov_match.group(1)))
            except Exception:
                pass
        return ProposalAdaptater.get_by_ref(str_val)


    @staticmethod
    def create(data: dict) -> dict:
        """Crée un devis (proposition commerciale) à l'état brouillon.

        data: client_id, lines=[{label, qty, price, vat}], date, validity_days, note.
        La validation du devis reste un acte manuel dans Dolibarr (§3.2).
        """
        try:
            lines = data.get("lines") or []
            if not lines:
                raise DolibarrClientError("Le devis doit contenir au moins une ligne.")
            validity = int(data.get("validity_days", 30))
            payload = {
                "socid": int(data.get("client_id")),
                "date": data.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "status": 0,  # brouillon — validation ultérieure par un utilisateur habilité
                "duree_validite": validity,
                "note_public": data.get("note", ""),
                "lines": [
                    {
                        "label": line.get("label", ""),
                        "qty": float(line.get("qty", 1)),
                        "subprice": float(line.get("price", 0)),
                        "tva_tx": float(line.get("vat", 0)),
                    }
                    for line in lines
                ],
            }
            result = DolibarrClientAdaptater.post("proposals", payload)
            # L'API renvoie l'identifiant en entier brut (ou un dict {id: ...} sur certaines versions)
            proposal_id = result if isinstance(result, int) else (result.get("id") if isinstance(result, dict) else None)
            if not proposal_id:
                raise DolibarrClientError(f"Création de devis sans identifiant retourné: {result}")
            # La ref (ex. "(PROV8)" en brouillon) n'est pas renvoyée par le POST : on la récupère
            # via GET /proposals/{id} — nécessaire pour générer le PDF (§4.4).
            ref = result.get("ref") if isinstance(result, dict) else None
            if not ref:
                try:
                    detail = DolibarrClientAdaptater.get(f"proposals/{int(proposal_id)}")
                    ref = detail.get("ref") if isinstance(detail, dict) else None
                except DolibarrClientError as e:
                    logger.warning(f"ProposalAdaptater: ref non récupérée après création: {e}")
            return {"id": proposal_id, "ref": ref}
        except DolibarrClientError as e:
            logger.error(f"ProposalAdaptater.create failed: {e}")
            raise e
