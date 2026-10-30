"""Demo evidence is visible only inside an explicitly isolated demo database."""

from sqlalchemy import true

from .config import get_settings


def evidence_visibility(model):
    # Settings validates the gridwatch_demo_ database namespace before this is true.
    return true() if get_settings().demo_instance else model.is_demo.is_(False)
