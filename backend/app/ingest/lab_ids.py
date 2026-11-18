"""Find lab IDs (mice, virus batches, experiments, cohorts) in text.

Written the same way across files, IDs vary: "m-42", "M-042", "M_042",
"M–042" (en dash). We normalise them to one canonical code so "which
documents mention M-042?" finds every spelling.
"""

import re
from collections import Counter
from dataclasses import dataclass

# prefix -> (entity_type, digits to zero-pad to)
PREFIXES: dict[str, tuple[str, int]] = {
    "M": ("mouse", 3),
    "V": ("virus_batch", 3),
    "EXP": ("experiment", 3),
    "C": ("cohort", 2),
}

# \b on both sides so "ABC-12" or "M-0421a" don't match.
# Longest prefix first so EXP is not read as something shorter.
LAB_ID = re.compile(r"\b(EXP|M|V|C)[-_\u2010-\u2013](\d{1,4})\b", re.IGNORECASE)


@dataclass(frozen=True)
class LabId:
    code: str  # canonical, e.g. "M-042"
    entity_type: str  # one of entities.entity_type


def normalise(prefix: str, number: str) -> LabId:
    prefix = prefix.upper()
    entity_type, width = PREFIXES[prefix]
    return LabId(f"{prefix}-{int(number):0{width}d}", entity_type)


def find_lab_ids(text: str) -> Counter[LabId]:
    """Every lab ID in the text, with how many times it is mentioned."""
    return Counter(normalise(m[1], m[2]) for m in LAB_ID.finditer(text))
