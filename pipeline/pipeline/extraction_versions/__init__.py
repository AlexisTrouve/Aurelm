"""Extraction version registry package.

Imports all version families and merges them into the global registry.
Public API (unchanged from the old extraction_versions.py module):
    get_version(name)     -> ExtractionVersion
    list_versions()       -> list[str]
    ExtractionVersion     (dataclass)
    VALIDATE_VERSIONS     (dict for benchmark_validate.py)
"""
from . import base
from .base import ExtractionVersion, get_version, list_versions
from .validate import VALIDATE_VERSIONS

# Import per-family version dicts
from .v1 import _VERSIONS_V1, V1_BASELINE
from .v2 import _VERSIONS_V2
from .v3 import _VERSIONS_V3
from .v4 import _VERSIONS_V4
from .v5 import _VERSIONS_V5
from .v6 import _VERSIONS_V6
from .v8 import _VERSIONS_V8
from .v9 import _VERSIONS_V9
from .v10 import _VERSIONS_V10
from .v11 import _VERSIONS_V11
from .v12 import _VERSIONS_V12
from .v13 import _VERSIONS_V13
from .v14 import _VERSIONS_V14
from .v15 import _VERSIONS_V15
from .v16 import _VERSIONS_V16
from .v17 import _VERSIONS_V17
from .v18 import _VERSIONS_V18
from .v19 import _VERSIONS_V19
from .v20 import _VERSIONS_V20
from .v21 import _VERSIONS_V21
from .v22 import _VERSIONS_V22

# Merge all families into base._VERSIONS (used by get_version / list_versions)
base._VERSIONS.update(_VERSIONS_V1)
base._VERSIONS.update(_VERSIONS_V2)
base._VERSIONS.update(_VERSIONS_V3)
base._VERSIONS.update(_VERSIONS_V4)
base._VERSIONS.update(_VERSIONS_V5)
base._VERSIONS.update(_VERSIONS_V6)
base._VERSIONS.update(_VERSIONS_V8)
base._VERSIONS.update(_VERSIONS_V9)
base._VERSIONS.update(_VERSIONS_V10)
base._VERSIONS.update(_VERSIONS_V11)
base._VERSIONS.update(_VERSIONS_V12)
base._VERSIONS.update(_VERSIONS_V13)
base._VERSIONS.update(_VERSIONS_V14)
base._VERSIONS.update(_VERSIONS_V15)
base._VERSIONS.update(_VERSIONS_V16)
base._VERSIONS.update(_VERSIONS_V17)
base._VERSIONS.update(_VERSIONS_V18)
base._VERSIONS.update(_VERSIONS_V19)
base._VERSIONS.update(_VERSIONS_V20)
base._VERSIONS.update(_VERSIONS_V21)
base._VERSIONS.update(_VERSIONS_V22)

__all__ = ["ExtractionVersion", "get_version", "list_versions", "VALIDATE_VERSIONS", "V1_BASELINE"]
