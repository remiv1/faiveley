# API Techniciens

## Situation actuelle du POC

L'application techniciens utilise le socle commun de service terrain pour consulter et traiter les demandes de maintenance enregistrées dans PostgreSQL. Elle distingue les demandes liées à une raison qualité de celles liées à une raison technique.

Les écrans Flask sont actualisés avec HTMX. Le POC ne distribue pas encore de notification temps réel lorsqu'une demande de maintenance est créée depuis la production.

## Solution retenue pour la production

La production publiera les événements métier dans Redis Streams. Le service techniciens consommera le flux `faiveley:production:events` avec le groupe `faiveley:techniciens`.

Les événements utiles sont notamment :

- `maintenance_request.created` ;
- `request.status_changed`.

Le consommateur utilisera `request_id` pour relire la demande complète dans PostgreSQL avant de l'afficher. PostgreSQL reste la source de vérité ; Redis ne stocke pas le dossier métier de maintenance.

Le traitement devra être idempotent et le message ne sera confirmé avec `XACK` qu'après un traitement réussi. Les messages en erreur resteront récupérables et les demandes ouvertes seront relues dans PostgreSQL après une reconnexion.

SSE pourra ensuite transmettre la notification au navigateur et déclencher le rechargement du fragment HTMX. Cette fonctionnalité appartient à la solution de production et n'est pas implémentée dans le POC.
