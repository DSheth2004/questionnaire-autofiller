"""Turn Google's VSAQ questionnaires into the Excel format vendors usually receive.

Usage:  python scripts/build_sample.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from autofill.questionnaire import load_vsaq, write_questions_xlsx  # noqa: E402

questions = []
for name in ("security_privacy_programs", "infrastructure", "webapp"):
    questions += load_vsaq(ROOT / "data" / "raw" / "vsaq" / f"{name}.json")
out = ROOT / "data" / "samples" / "vsaq_questionnaire.xlsx"
write_questions_xlsx(questions, out)
print(f"{len(questions)} questions -> {out.relative_to(ROOT)}")
