"""PydanticAI agents that replace the LLM-driven LangGraph nodes.

Each agent has two modes:
- LLM mode: PydanticAI Agent backed by OpenRouter, used when
  settings.OPENROUTER_API_KEY is set.
- Fallback mode: deterministic regex/rule-based logic (matches the eval
  ScriptedLLM in lang-graph/evals/fakes.py). Used when the LLM key is
  empty — keeps evals fully offline and gives a sensible dev experience.

Agents:
- IntentAgent       — classify intent (qualification / service_inquiry / booking / faq / objection)
- ExtractionAgent   — pull customer + pet fields from free text
- FaqAgent          — 1-3 sentence answer grounded in BrandConfig
- ObjectionAgent    — empathetic 2-4 sentence response + suggested alternative
"""
