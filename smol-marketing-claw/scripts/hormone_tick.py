"""SessionStart hook — apply hormone decay via DigitalHormones class."""

import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = PLUGIN_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.hormones import DigitalHormones
from src.usage import UsageTracker


def main():
    memory_dir = PROJECT_ROOT / "memory"
    if not memory_dir.exists():
        return

    try:
        usage = UsageTracker(usage_file=str(memory_dir / "usage.json"))
        hormones = DigitalHormones(
            state_file=str(memory_dir / "hormones.json"),
            usage_tracker=usage,
        )
        hormones.decay()
        hormones.save_state()

        s = hormones.state
        print(
            f"Hormone tick: dopamine={s.dopamine:.3f}, cortisol={s.cortisol:.3f}, tick={s.tick_count}",
            file=sys.stderr,
        )
    except Exception as e:
        print(f"Hormone tick failed: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
