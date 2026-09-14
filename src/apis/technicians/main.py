"""Point d'entrée de l'API Flask dédiée aux techniciens."""

from common.field_service import FieldServiceConfig, create_field_service_app
from common.models.production import MaintenanceRequest
from common.models.users import TECHNICIENS

app = create_field_service_app(
    FieldServiceConfig(
        name="techniciens",
        title="Techniciens",
        permission=TECHNICIENS,
        request_model=MaintenanceRequest,
    )
)
