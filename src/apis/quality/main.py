"""Point d'entrée de l'API Flask dédiée au service qualité."""

from apis.field_service import FieldServiceConfig, create_field_service_app
from common.models.production import QualitySupportRequest
from common.models.users import QUALITE

app = create_field_service_app(
    FieldServiceConfig(
        name="qualite",
        title="Qualité",
        permission=QUALITE,
        request_model=QualitySupportRequest,
    )
)
