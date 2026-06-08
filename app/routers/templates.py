"""Lists the PDF templates a user can pick from."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..auth import require_user
from ..pdf_templates import DEFAULT_TEMPLATE_ID, list_templates
from ..schemas import TemplateInfoResponse, TemplateListResponse

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("", response_model=TemplateListResponse)
def list_pdf_templates(
    _user: dict[str, str] = Depends(require_user),
) -> TemplateListResponse:
    """Return the catalogue of PDF templates a user can pick from."""
    return TemplateListResponse(
        templates=[
            TemplateInfoResponse(
                id=t.id, name=t.name, description=t.description, tagline=t.tagline
            )
            for t in list_templates()
        ],
        default_id=DEFAULT_TEMPLATE_ID,
    )
