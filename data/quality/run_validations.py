"""Run Great Expectations validations."""

import sys
from pathlib import Path

import great_expectations as gx


def run_checkpoint(checkpoint_name: str) -> bool:
    """Run a GE checkpoint and return success status."""
    context = gx.get_context(context_root_dir=Path(__file__).parent / "great_expectations")

    result = context.run_checkpoint(checkpoint_name=checkpoint_name)

    if not result.success:
        print(f"❌ Checkpoint {checkpoint_name} FAILED")
        for validation_result in result.run_results.values():
            for result_item in validation_result.get("validation_result", {}).get("results", []):
                if not result_item.get("success"):
                    print(
                        f"  - {result_item.get('expectation_config', {}).get('expectation_type')}"
                    )
        return False

    print(f"✅ Checkpoint {checkpoint_name} PASSED")
    return True


def run_all() -> bool:
    """Run all checkpoints."""
    checkpoints = ["bronze_checkpoint", "silver_checkpoint", "gold_checkpoint"]
    results = []

    for cp in checkpoints:
        try:
            results.append(run_checkpoint(cp))
        except Exception as e:
            print(f"❌ Checkpoint {cp} ERROR: {e}")
            results.append(False)

    return all(results)


if __name__ == "__main__":
    checkpoint = sys.argv[1] if len(sys.argv) > 1 else None

    if checkpoint:
        success = run_checkpoint(checkpoint)
    else:
        success = run_all()

    sys.exit(0 if success else 1)
