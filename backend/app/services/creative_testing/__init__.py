"""
Creative Testing module (additive, opt-in).

Implementa Fase 1 del ROADMAP_CREATIVE_TESTING_90D como capa paralela
al pipeline de reportes existente. Se activa via Config.CREATIVE_TESTING_ENABLED
y no modifica contratos ni rutas previas.
"""

from .schema import (
    CreativeTestRequest,
    CreativeVariant,
    AudienceProfile,
    SuccessMetric,
    parse_request,
    validate_request,
    ValidationError,
)
from .store import CreativeTestStore
from .mock_runner import generate_mock_result
from .runner import run as run_creative_test, STAGES as CT_STAGES

__all__ = [
    "CreativeTestRequest",
    "CreativeVariant",
    "AudienceProfile",
    "SuccessMetric",
    "parse_request",
    "validate_request",
    "ValidationError",
    "CreativeTestStore",
    "generate_mock_result",
    "run_creative_test",
    "CT_STAGES",
]
