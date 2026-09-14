# API Qualité

## Situation actuelle du POC

L'application qualité utilise le socle commun de service terrain pour consulter et traiter les demandes de support qualité enregistrées dans PostgreSQL.

L'interface est rendue par Flask et actualisée avec HTMX. Le POC ne reçoit pas encore de notification immédiate lorsqu'un opérateur crée une demande depuis la production.

## Solution retenue pour la production

La production publiera les événements métier dans Redis Streams. Le service qualité consommera le flux `faiveley:production:events` avec le groupe `faiveley:qualite`.

Les événements utiles sont notamment :

- `quality_support_request.created` ;
- `request.status_changed`.

Après réception, le service relira la demande complète depuis PostgreSQL avant de l'afficher ou de la traiter. PostgreSQL reste la source de vérité et Redis sert uniquement à distribuer les événements.

Le consommateur devra traiter les messages de façon idempotente et utiliser `XACK` uniquement après un traitement réussi. Un message en erreur devra rester récupérable. Une reconnexion déclenchera également un rechargement des demandes ouvertes depuis PostgreSQL.

SSE pourra être ajouté pour transmettre la notification au navigateur et recharger le fragment HTMX concerné. Cette évolution n'est pas implémentée dans le POC actuel.
