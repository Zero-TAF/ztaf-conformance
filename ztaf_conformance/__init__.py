"""ztaf-conformance: the must-fail fixture runner and the ztaf-audit engine.

Reference only. The normative conformance clauses (ZT-CC) live in ztaf-spec;
the certification process outline lives in docs/ of this repository.
"""

from .audit import audit, render
from .fixtures import run_all

__version__ = "0.1.0"
