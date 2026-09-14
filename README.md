# FaiveleyTech (POC)

This POC is edited to demonstrate at the C-Suite, the potential with changing processes in the production area.

Today, this is a paper-world, where each worker create data by writing in papers, re-write using batchings in an excel tab and a poor quality data is generated.

The C-Suite takes decisions with these datas.

In a near futur, we can have numerical consol on each press limiting enters, having more efficiency and perhaps, connecting machine-datas to dataset in an etl worker.

## Situation actuelle du POC

Le POC est constitué de plusieurs applications Flask séparées :

- la production, utilisée depuis une console associée à une presse ;
- la manutention, la qualité et les techniciens, qui traitent les demandes ;
- le dashboard, qui administre les utilisateurs et les paramètres du POC.

Les demandes métier et les données de production sont enregistrées dans PostgreSQL. Les interfaces utilisent HTMX pour soumettre les actions et recharger les fragments HTML. Les services consultent donc les demandes enregistrées lorsqu'un écran est chargé ou actualisé.

Cette solution est suffisante pour le POC, mais elle ne fournit pas encore de distribution temps réel entre les services. Une demande créée en production peut nécessiter un rechargement de l'écran de la manutention, de la qualité ou des techniciens avant d'être visible.

## Solution retenue pour la production

La solution cible repose sur **Redis Streams** pour distribuer les événements entre les applications. PostgreSQL reste la source de vérité pour les données métier ; Redis ne remplace pas le stockage des demandes.

```text
Console de production
    |
    | écriture métier
    v
PostgreSQL <---------------- source de vérité
    |
    | événement
    v
Redis Streams
    |
    +--> groupe manutention
    +--> groupe qualité
    +--> groupe techniciens
```

Lorsqu'une demande est créée ou que son statut change, l'application publie un événement dans un flux Redis commun, par exemple `faiveley:production:events`. Les services concernés consomment ce flux avec leur propre groupe de consommateurs :

- `faiveley:manutention` ;
- `faiveley:qualite` ;
- `faiveley:techniciens`.

Le message Redis contient un identifiant d'événement, son type, sa date, ainsi que l'identifiant de la demande et du poste. Le consommateur recharge ensuite la demande complète depuis PostgreSQL avant de l'afficher.

Les événements retenus sont notamment :

- `supply_request.created` ;
- `logistics_support_request.created` ;
- `quality_support_request.created` ;
- `maintenance_request.created` ;
- `request.status_changed`.

Les consommateurs doivent être idempotents et confirmer un message avec `XACK` uniquement après son traitement. Les messages en erreur restent rejouables. À la reconnexion, chaque interface recharge également les demandes ouvertes depuis PostgreSQL afin de récupérer une éventuelle notification manquée.

La diffusion vers les navigateurs pourra ensuite utiliser SSE (Server-Sent Events). Cette couche sera ajoutée lors de l'implémentation temps réel ; elle n'est pas incluse dans le POC actuel.

## Déploiement cible documenté

Redis sera ajouté au réseau interne Docker avec un volume persistant. Les services utiliseront notamment les paramètres suivants :

```text
REDIS_URL=redis://redis:6379/0
REDIS_STREAM=faiveley:production:events
REDIS_CONSUMER_GROUP=faiveley:<service>
REDIS_CONSUMER_NAME=<hostname>
```

La migration sera progressive : ajout de Redis, publication depuis la production, ajout des consommateurs métier, puis ajout du rafraîchissement temps réel des écrans. Le rechargement HTMX périodique pourra rester un mécanisme de récupération tant que la reprise sur erreur n'est pas validée.
