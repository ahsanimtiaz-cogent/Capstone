"""Qualification business logic: persist lead/pet rows to Sheets and flip status."""
from ..base_client import BaseMCPClient
from ..mcp_utils import get_sheets
from .models import (
    GetQualificationStatusRequest,
    GetQualificationStatusResponse,
    QualifyLeadRequest,
    QualifyLeadResponse,
)


class QualificationMCPClient(BaseMCPClient):
    """Wraps SheetsRepo for lead qualification.

    Behavior mirrors lang-graph/graph/nodes/qualify.py: flip status to
    'qualified', append a Pets row if a matching pet (name+breed) doesn't
    already exist.
    """

    def qualify_lead(self, request: QualifyLeadRequest) -> QualifyLeadResponse:
        sheets = get_sheets()
        if not self.lead_id:
            return QualifyLeadResponse(
                qualified=False, lead_id="",
                error="Missing _lead_id metadata; cannot qualify without a lead.",
            )

        try:
            sheets.set_lead_status(self.lead_id, "qualified")
        except Exception as e:
            self.logger.warning("Could not flip lead status: %s", e)

        pet_id = None
        try:
            existing = sheets.list_pets_for_lead(self.lead_id)
            signature = (
                request.pet.name.strip().lower(),
                request.pet.breed.strip().lower(),
            )
            already = any(
                (p.get("pet_name", "").strip().lower(),
                 p.get("breed", "").strip().lower()) == signature
                for p in existing
            )
            if not already:
                pet_id = sheets.append_pet(self.lead_id, {
                    "name": request.pet.name,
                    "breed": request.pet.breed,
                    "weight": request.pet.weight,
                    "age": request.pet.age,
                    "coat": request.pet.coat,
                    "notes": request.note,
                })
        except Exception as e:
            self.logger.warning("Could not append pet record: %s", e)

        # Best-effort: keep Sheets Leads row in sync with provided contact info
        try:
            updates = {}
            if request.name:
                updates["name"] = request.name
            if request.phone:
                updates["phone"] = request.phone
            if updates:
                sheets.update_lead(self.lead_id, **updates)
        except Exception as e:
            self.logger.warning("Could not update lead contact fields: %s", e)

        return QualifyLeadResponse(qualified=True, lead_id=self.lead_id, pet_id=pet_id)

    def get_qualification_status(
        self, _request: GetQualificationStatusRequest
    ) -> GetQualificationStatusResponse:
        sheets = get_sheets()
        lead = None
        if self.lead_id:
            # Lookup by discord_user_id is the cheap path; fall back to a scan.
            if self.discord_user_id:
                lead = sheets.get_lead_by_discord_id(self.discord_user_id)
            if not lead:
                for row in sheets._leads.get_all_records():  # noqa: SLF001 - acceptable for read-only scan
                    if row.get("lead_id") == self.lead_id:
                        lead = row
                        break
        pets = sheets.list_pets_for_lead(self.lead_id) if self.lead_id else []
        pet = {}
        if pets:
            pet = {
                "name": pets[0].get("pet_name", ""),
                "breed": pets[0].get("breed", ""),
                "weight": str(pets[0].get("weight_kg", "")),
                "age": str(pets[0].get("age_years", "")),
                "coat": pets[0].get("coat_condition", ""),
            }
        return GetQualificationStatusResponse(
            lead_id=self.lead_id,
            status=(lead or {}).get("status", "unknown"),
            name=(lead or {}).get("name", ""),
            phone=(lead or {}).get("phone", ""),
            pet=pet,
        )
