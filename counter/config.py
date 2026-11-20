"""Application paths. Runtime configuration remains environment based."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PUBLIC_ROOT = PROJECT_ROOT / "public"
