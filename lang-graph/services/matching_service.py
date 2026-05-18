import difflib
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


def parse_weight_kg(weight: Any) -> Optional[float]:
    if weight is None:
        return None
    if isinstance(weight, (int, float)):
        return float(weight)
    text = str(weight).strip().lower()
    match = _NUM_RE.search(text)
    if not match:
        return None
    return float(match.group(0))


def _bracket_for_weight(brackets: List[Dict[str, Any]], weight_kg: float
                        ) -> Tuple[Optional[Dict[str, Any]], bool]:
    """Return (bracket, is_fallback). Fallback = pet weight is outside all brackets."""
    if not brackets:
        return None, False
    for b in brackets:
        if float(b.get("min", 0)) <= weight_kg <= float(b.get("max", 0)):
            return b, False
    # Fallback: pick the closest bracket by distance
    def distance(b):
        lo = float(b.get("min", 0))
        hi = float(b.get("max", 0))
        if weight_kg < lo:
            return lo - weight_kg
        return weight_kg - hi
    closest = min(brackets, key=distance)
    return closest, True


def _breed_modifier(breed: str, modifier_map: Dict[str, float]) -> Tuple[float, Optional[str]]:
    if not breed or not modifier_map:
        return 1.0, None
    target = breed.strip().lower()
    best_key: Optional[str] = None
    best_score = 0.0
    for key in modifier_map.keys():
        score = difflib.SequenceMatcher(None, target, key.lower()).ratio()
        if score > best_score:
            best_score = score
            best_key = key
    if best_score >= 0.7 and best_key is not None:
        return float(modifier_map[best_key]), best_key
    return 1.0, None


def _service_title_score(pet_breed: str, service_title: str) -> float:
    if not pet_breed or not service_title:
        return 0.0
    return difflib.SequenceMatcher(
        None, pet_breed.strip().lower(), service_title.strip().lower()
    ).ratio()


def price_for_service(service: Dict[str, Any], pet: Dict[str, Any]
                      ) -> Tuple[float, bool, Optional[str]]:
    """Returns (final_price, is_fallback, fallback_reason)."""
    base = float(service.get("base_price", 0))
    weight = parse_weight_kg(pet.get("weight"))
    brackets = service.get("weight_brackets_json", []) or []

    bracket_mult = 1.0
    is_fallback = False
    fallback_reason: Optional[str] = None

    if weight is not None and brackets:
        bracket, is_fallback = _bracket_for_weight(brackets, weight)
        if bracket is not None:
            bracket_mult = float(bracket.get("mult", 1.0))
            if is_fallback:
                fallback_reason = (
                    f"Closest match for a {weight}kg pet "
                    f"(bracket {bracket.get('min')}-{bracket.get('max')}kg)."
                )

    breed_mult, _matched_breed = _breed_modifier(
        pet.get("breed", ""), service.get("breed_modifier_json", {}) or {}
    )

    final = base * bracket_mult * breed_mult
    return round(final, 2), is_fallback, fallback_reason


def find_best_service(pet: Dict[str, Any], services: List[Dict[str, Any]]
                      ) -> Optional[Dict[str, Any]]:
    """Recommend the single best service for a pet.

    Strategy: prefer services whose title fuzzy-matches breed; otherwise
    use the cheapest in-bracket Full Groom-like service.
    """
    if not services:
        return None

    pet_breed = pet.get("breed", "")
    scored: List[Tuple[float, Dict[str, Any]]] = []

    for svc in services:
        if "add-on" in svc.get("title", "").lower():
            continue  # skip add-ons as primary recommendations
        title_score = _service_title_score(pet_breed, svc.get("title", ""))
        scored.append((title_score, svc))

    if not scored:
        return None

    scored.sort(key=lambda x: (-x[0], x[1].get("base_price", 0)))
    chosen = scored[0][1]
    final_price, is_fallback, fallback_reason = price_for_service(chosen, pet)

    return {
        "service_id": chosen["service_id"],
        "title": chosen["title"],
        "description": chosen.get("description", ""),
        "base_price": chosen["base_price"],
        "final_price": final_price,
        "duration_min": chosen["duration_min"],
        "is_fallback": is_fallback,
        "fallback_reason": fallback_reason,
    }


def match_service_by_user_input(text: str, services: List[Dict[str, Any]]
                                ) -> Optional[Dict[str, Any]]:
    """Match a user's reply (service title, id, or fuzzy phrase) to a service."""
    if not text or not services:
        return None
    needle = text.strip().lower()

    for svc in services:
        if svc.get("service_id", "").lower() == needle:
            return svc

    for svc in services:
        if svc.get("title", "").lower() == needle:
            return svc

    best: Optional[Dict[str, Any]] = None
    best_score = 0.0
    for svc in services:
        score = difflib.SequenceMatcher(
            None, needle, svc.get("title", "").lower()
        ).ratio()
        if score > best_score:
            best_score = score
            best = svc

    if best_score >= 0.55:
        return best
    return None


def format_services_list(services: List[Dict[str, Any]], pet: Dict[str, Any],
                         recommended_id: Optional[str] = None) -> str:
    lines = []
    for svc in services:
        price, is_fallback, _reason = price_for_service(svc, pet)
        prefix = "→ " if svc.get("service_id") == recommended_id else "• "
        lines.append(
            f"{prefix}{svc['title']} — ${price:.2f} ({svc['duration_min']} min)"
        )
    return "\n".join(lines)
