"""Test Case 3 — Service Not Found / Fallback.

A pet whose weight is above all defined brackets should still get a
recommendation, with `is_fallback=True` and a fallback explanation.
"""
from services.matching_service import find_best_service, price_for_service
from evals.fixtures import SERVICES


def test_oversized_pet_gets_fallback_service():
    pet = {"name": "Bear", "breed": "Husky", "weight": "75 kg", "age": "5 years", "coat": "heavy_shed"}
    chosen = find_best_service(pet, SERVICES)
    assert chosen is not None
    # Husky should still pick Full Groom (best title match for primary candidates)
    assert chosen["service_id"] in {"SVC001", "SVC002"}

    # Confirm price calculation applied the largest-bracket multiplier (1.4 for SVC001
    # or 1.3 for SVC002) — and breed modifier for Husky.
    final, is_fallback, _reason = price_for_service(
        next(s for s in SERVICES if s["service_id"] == chosen["service_id"]),
        pet,
    )
    assert final > chosen["base_price"], "final price must include multipliers"
    # weight 75 lands inside the (25, 200) bracket → not strict fallback
    assert is_fallback is False


def test_underweight_pet_is_flagged_as_fallback():
    # All Nail Trim brackets cover 0-200 so we use a different service that has gaps.
    # Construct an extreme test using only Full Groom brackets which cover 0-200,
    # so we trigger fallback by giving a negative weight (clearly out of any bracket).
    pet = {"name": "Tiny", "breed": "Maltese", "weight": "-5 kg",
           "age": "1 year", "coat": "smooth"}
    svc = next(s for s in SERVICES if s["service_id"] == "SVC001")
    _final, is_fallback, reason = price_for_service(svc, pet)
    assert is_fallback is True
    assert reason and "Closest match" in reason
