# API Techniciens

## Accès et changement d'environnement

Accès via Nginx : `http://localhost:8110/techniciens/entree`, puis connexion propre
aux techniciens. Le service n'expose plus de port hôte direct.

Le sélecteur commun est présent sur la connexion et la vue des demandes.
Changer d'environnement ou se déconnecter révoque le jeton courant en base et
supprime la session locale. L'arrivée dans le service cible efface également son
ancienne session avant la connexion. Ces opérations utilisent des `POST` protégés
par CSRF, avec un bouton « Continuer » à l'arrivée si JavaScript est désactivé.
Le cookie `techniciens_session` est limité à `/techniciens` ; les sessions d'autres
appareils ne sont pas révoquées.

## Situation actuelle du POC

L'application techniciens utilise le socle commun de service terrain pour consulter et traiter les demandes de maintenance enregistrées dans PostgreSQL. Elle distingue les demandes liées à une raison qualité de celles liées à une raison technique.

Les écrans Flask sont actualisés avec HTMX. Le POC ne distribue pas encore de notification temps réel lorsqu'une demande de maintenance est créée depuis la production.

## Solution retenue pour la production

La production publiera les événements métier dans Redis Streams. Le service techniciens consommera le flux `plasturgie:production:events` avec le groupe `plasturgie:techniciens`.

Les événements utiles sont notamment :

- `maintenance_request.created` ;
- `request.status_changed`.

Le consommateur utilisera `request_id` pour relire la demande complète dans PostgreSQL avant de l'afficher. PostgreSQL reste la source de vérité ; Redis ne stocke pas le dossier métier de maintenance.

Le traitement devra être idempotent et le message ne sera confirmé avec `XACK` qu'après un traitement réussi. Les messages en erreur resteront récupérables et les demandes ouvertes seront relues dans PostgreSQL après une reconnexion.

SSE pourra ensuite transmettre la notification au navigateur et déclencher le rechargement du fragment HTMX. Cette fonctionnalité appartient à la solution de production et n'est pas implémentée dans le POC.
