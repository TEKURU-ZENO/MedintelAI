"""app/services/ml/__init__.py — Behavioral ML Layer (Phase 5)

Design contract:
  - NO external ML libraries (no sklearn, numpy, torch)
  - Pure Python weighted scoring + heuristics
  - ML as ADVISOR only — never controls core tracing/scoring
  - All outputs include: {value, confidence, source}
  - Shadow ML pattern: rule + ml run in parallel, delta logged
"""
