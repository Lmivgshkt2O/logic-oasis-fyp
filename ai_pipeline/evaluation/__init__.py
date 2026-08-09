"""AQC-2 offline policy-evaluation pipeline (Stage B, descriptive only).

This package reconstructs P1/P2/P3a decisions from trusted chronological
histories without future leakage.  It never claims causality and never scores
a candidate whose selected difficulty differs from the actually delivered
difficulty.
"""

from __future__ import annotations

