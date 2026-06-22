"""
Migration module: safely move a knowledge base between embedding models.

The hardest module — saved for last because it benefits from all other pieces
being in place. Strategy:
  1. Re-embed all chunks with the new model (shadow index)
  2. Run evaluation to validate quality hasn't degraded
  3. If quality is acceptable, perform the cutover
  4. Keep the old index as backup until confirmed

Quick start:
    from ragforge.migration import migrate_knowledge_base

    result = migrate_knowledge_base(
        knowledge="my-kb",
        from_model="default",
        to_model="quantized",
    )

Gated migration (recommended):
    from ragforge.migration import migrate_with_gate

    result = migrate_with_gate(
        knowledge="my-kb",
        from_model="default",
        to_model="openai",
        golden_path="golden.json",
    )
    # Runs decision gate first — aborts if new model regresses.

Decision gate only (no migration):
    from ragforge.migration.gate import run_decision_gate
"""

from ragforge.migration.migrator import migrate_knowledge_base, migrate_with_gate
from ragforge.migration.gate import run_decision_gate, GateDecision, identify_hot_set, smoke_test, SmokeTestResult

__all__ = [
    "migrate_knowledge_base",
    "migrate_with_gate",
    "run_decision_gate",
    "GateDecision",
    "identify_hot_set",
    "smoke_test",
    "SmokeTestResult",
]
