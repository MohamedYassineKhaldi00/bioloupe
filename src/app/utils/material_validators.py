from __future__ import annotations

from app.core.exceptions import BioLoupeException
from app.models import MaterialType
from app.schemas.material_metadata import (
    ExperimentMetadata,
    ImageMetadata,
    NoteMetadata,
    PaperMetadata,
    SequenceMetadata,
)


def validate_material_metadata(material_type: MaterialType, metadata: dict | None) -> dict:
    if metadata is None:
        return {}

    try:
        if material_type == MaterialType.paper:
            return PaperMetadata(**metadata).model_dump(exclude_none=True)
        if material_type == MaterialType.sequence:
            return SequenceMetadata(**metadata).model_dump(exclude_none=True)
        if material_type == MaterialType.image:
            return ImageMetadata(**metadata).model_dump(exclude_none=True)
        if material_type == MaterialType.experiment:
            return ExperimentMetadata(**metadata).model_dump(exclude_none=True)
        if material_type == MaterialType.note:
            return NoteMetadata(**metadata).model_dump(exclude_none=True)
    except Exception as exc:
        raise BioLoupeException(f"Invalid metadata: {exc}") from exc

    raise BioLoupeException("Unsupported material type")
