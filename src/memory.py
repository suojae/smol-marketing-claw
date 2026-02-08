"""Memory management system."""

import json
import uuid
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List


class SimpleMemory:
    """Simple JSON-based memory management with no external dependencies"""

    def __init__(self, memory_dir: str = "memory"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        self.max_decisions = 100
        self.decisions_file = self.memory_dir / "decisions.json"
        self.summary_file = self.memory_dir / "summary.txt"

    def load_decisions(self) -> List[Dict[str, Any]]:
        """Load decisions from JSON file"""
        if not self.decisions_file.exists():
            return []
        try:
            with open(self.decisions_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load decisions: {e}")
            return []

    def save_decisions(self, decisions: List[Dict[str, Any]]):
        """Save decisions to JSON file"""
        try:
            with open(self.decisions_file, "w", encoding="utf-8") as f:
                json.dump(decisions, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save decisions: {e}")

    def load_summary(self) -> str:
        """Load summary from text file"""
        if not self.summary_file.exists():
            return "No previous activity."
        try:
            return self.summary_file.read_text(encoding="utf-8")
        except Exception:
            return "No previous activity."

    def save_summary(self, summary: str):
        """Save summary to text file"""
        try:
            self.summary_file.write_text(summary, encoding="utf-8")
        except Exception as e:
            print(f"Failed to save summary: {e}")

    def add_decision(self, decision: Dict[str, Any]):
        """Add a new decision and auto-manage memory"""
        decisions = self.load_decisions()

        # Add new decision with metadata
        decision_entry = {
            "id": str(uuid.uuid4())[:8],
            "timestamp": datetime.now().isoformat(),
            **decision
        }
        decisions.append(decision_entry)

        # If exceeded max, create summary of old decisions
        if len(decisions) > self.max_decisions:
            old_decisions = decisions[:50]
            decisions = decisions[50:]

            # Create simple summary
            summary = self._create_summary(old_decisions)
            self.save_summary(summary)
            print(f"Created summary of {len(old_decisions)} old decisions")

        self.save_decisions(decisions)

    def _create_summary(self, decisions: List[Dict[str, Any]]) -> str:
        """Create a simple text summary of decisions"""
        if not decisions:
            return "No previous activity."

        total = len(decisions)
        actions = Counter([d.get("action", "unknown") for d in decisions])
        first_date = decisions[0].get("timestamp", "unknown")
        last_date = decisions[-1].get("timestamp", "unknown")

        summary = f"""Summary of {total} decisions ({first_date} to {last_date}):
- Total actions: {total}
- Action breakdown: {dict(actions)}
- Most common action: {actions.most_common(1)[0][0] if actions else 'none'}
"""
        return summary

    def get_context(self) -> str:
        """Get memory context for AI"""
        summary = self.load_summary()
        recent = self.load_decisions()[-10:]  # Last 10 decisions

        if not recent:
            return "[Memory] No recent activity."

        recent_text = "\n".join([
            f"- [{d.get('timestamp', 'unknown')}] {d.get('action', 'unknown')}: {d.get('message', 'N/A')[:50]}"
            for d in recent
        ])

        return f"""[Long-term Memory]
{summary}

[Recent Activity (Last 10)]
{recent_text}
"""

    def should_skip_duplicate(self, message: str) -> bool:
        """Check if this message was sent recently (24h window)"""
        decisions = self.load_decisions()
        yesterday = datetime.now() - timedelta(days=1)

        for d in decisions:
            try:
                decision_time = datetime.fromisoformat(d.get("timestamp", ""))
                if decision_time > yesterday:
                    prev_message = d.get("message", "")
                    if self._similarity(message, prev_message) > 0.85:
                        print(f"Skipping duplicate: '{message[:50]}...'")
                        return True
            except Exception:
                continue

        return False

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        """Calculate simple word-based similarity"""
        if not a or not b:
            return 0.0

        words_a = set(a.lower().split())
        words_b = set(b.lower().split())

        if not words_a or not words_b:
            return 0.0

        intersection = words_a & words_b
        union = words_a | words_b

        return len(intersection) / len(union)


class GuardrailMemory(SimpleMemory):
    """Security-focused memory"""

    def __init__(self, memory_dir: str = "memory"):
        super().__init__(memory_dir)
        self.violations_file = self.memory_dir / "guardrail_violations.json"

    def load_violations(self) -> List[Dict[str, Any]]:
        """Load guardrail violations"""
        if not self.violations_file.exists():
            return []
        try:
            with open(self.violations_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def save_violations(self, violations: List[Dict[str, Any]]):
        """Save guardrail violations"""
        try:
            with open(self.violations_file, "w", encoding="utf-8") as f:
                json.dump(violations, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save violations: {e}")

    def record_violation(self, violation_type: str, target: str, reason: str):
        """Record a guardrail violation"""
        violations = self.load_violations()

        violation_entry = {
            "id": str(uuid.uuid4())[:8],
            "timestamp": datetime.now().isoformat(),
            "type": violation_type,
            "target": target,
            "reason": reason,
            "blocked": True
        }

        violations.append(violation_entry)
        self.save_violations(violations)

        print(f"Guardrail violation recorded: {violation_type} on {target}")

    def get_safety_context(self) -> str:
        """Get security context for AI"""
        violations = self.load_violations()

        if not violations:
            return "[Security] No violations recorded."

        # Get recent violations (last 20)
        recent = violations[-20:]

        # Find patterns
        frequent_targets = Counter([v.get("target") for v in recent])
        frequent_types = Counter([v.get("type") for v in recent])

        safety_text = f"""[Security History]
Total violations blocked: {len(violations)}
Recent violations: {len(recent)}

Most frequently attempted:
{chr(10).join([f'  - {target}: {count} times' for target, count in frequent_targets.most_common(3)])}

Violation types:
{chr(10).join([f'  - {vtype}: {count} times' for vtype, count in frequent_types.most_common(3)])}

Be extra careful with these targets!
"""
        return safety_text
