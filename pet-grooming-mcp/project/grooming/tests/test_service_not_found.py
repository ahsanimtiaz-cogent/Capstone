"""Test 5 — Fallback pricing for an out-of-bracket pet.

Ported from lang-graph/evals/test_service_not_found.py — exercises the
matching service directly (no Coordinator round-trip needed).
"""
from project.grooming.integrations.matching_service import (
    find_best_service,
    price_for_service,
)

from .fixtures import SERVICES


def test_oversized_pet_gets_fallback_service():
    pet = {"name": "Bear", "breed": "Husky", "weight": "75 kg",
           "age": "5 years", "coat": "heavy_shed"}
    chosen = find_best_service(pet, SERVICES)
    assert chosen is not None
    assert chosen["service_id"] in {"SVC001", "SVC002"}

    final, is_fallback, _reason = price_for_service(
        next(s for s in SERVICES if s["service_id"] == chosen["service_id"]),
        pet,
    )
    assert final > chosen["base_price"]
    assert is_fallback is False


def test_underweight_pet_is_flagged_as_fallback():
    pet = {"name": "Tiny", "breed": "Maltese", "weight": "-5 kg",
           "age": "1 year", "coat": "smooth"}
    svc = next(s for s in SERVICES if s["service_id"] == "SVC001")
    _final, is_fallback, reason = price_for_service(svc, pet)
    assert is_fallback is True
    assert reason and "Closest match" in reason
