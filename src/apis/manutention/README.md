# API Manutention

## Situation actuelle du POC

L'application permet aux manutentionnaires authentifiés de consulter les demandes d'approvisionnement et de support logistique enregistrées dans PostgreSQL. Les demandes peuvent être prises en charge puis résolues depuis l'interface HTMX.

La liste des demandes est rechargée par les endpoints Flask lorsque l'écran est chargé ou actualisé. Le POC ne reçoit pas encore de notification temps réel lorsqu'une nouvelle demande est créée en production.

## Solution retenue pour la production

La production publiera les événements métier dans Redis Streams. La manutention consommera le flux `faiveley:production:events` avec le groupe `faiveley:manutention`.

Les événements utiles sont notamment :

- `supply_request.created` ;
- `logistics_support_request.created` ;
- `request.status_changed`.

Le consommateur utilisera `request_id` pour relire la demande dans PostgreSQL, qui reste la source de vérité. Il ne reconstruira pas une demande uniquement à partir du message Redis.

Un message sera confirmé avec `XACK` uniquement après le traitement réussi. Les traitements seront idempotents afin de supporter les reprises et les reconnexions. À chaque reconnexion, la liste des demandes ouvertes sera rechargée depuis PostgreSQL.

La diffusion de la notification vers le navigateur pourra ensuite utiliser SSE pour déclencher le rechargement des fragments HTMX. Cette évolution appartient à la solution de production et n'est pas implémentée dans le POC.
