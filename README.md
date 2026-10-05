# Plasturgie (POC)

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

## Répartiteur et navigation

Le point d'entrée unique est **<http://localhost:8110/>**. Nginx distribue les
requêtes aux applications du réseau Docker interne ; les anciens ports directs
des applications ne sont plus publiés.

| Environnement | Entrée depuis le portail | Accès métier |
| --- | --- | --- |
| Gestion | `/gestion/entree` | `/gestion/` |
| Production | `/production/entree` | `/production/` |
| Manutention | `/manutention/entree` | `/manutention/` |
| Qualité | `/qualite/entree` | `/qualite/` |
| Techniciens | `/techniciens/entree` | `/techniciens/` |

Chaque écran de connexion et chaque vue principale propose un sélecteur
d'environnement. Son action déconnecte l'environnement courant, puis efface
l'ancienne session de l'environnement cible avant d'afficher sa connexion.
Il n'y a ni connexion commune ni partage d'identité entre applications.
Une entrée directe depuis le portail réinitialise la destination ; pour
déconnecter également l'environnement de départ, utiliser son sélecteur.

Les déconnexions utilisent uniquement des `POST` protégés par CSRF. L'écran
intermédiaire d'arrivée soumet automatiquement son formulaire ; sans JavaScript,
le bouton « Continuer » permet de terminer le parcours. Les destinations sont
limitées aux cinq applications et les pages sensibles ne sont pas mises en cache.

En manutention, qualité et techniciens, seule la session correspondant au jeton
du navigateur est révoquée en base. Les sessions d'autres appareils ne sont pas
révoquées. La gestion et la production utilisent encore des cookies Flask signés :
leur suppression locale n'invalide pas côté serveur une copie antérieure du cookie.
Les cookies sont isolés par nom et par chemin ; les anciens cookies à la racine
sont supprimés progressivement, sans transférer l'identité gestion/production.

En production, revenir dans l'environnement demande de choisir une presse ayant
un poste actif, puis de valider à nouveau la présence de l'opérateur. Quitter la
console efface son contexte HTTP **sans clôturer le poste en base**.

### Démarrage

Définir `FLASK_SECRET_KEY` dans l'environnement ou le fichier `.env` de Compose,
et renseigner les paramètres PostgreSQL existants, puis lancer :

```bash
docker compose config --quiet
docker compose up -d --build
```

Avec Podman, utiliser `podman compose up -d --build`. La base doit déjà disposer
des migrations du projet, notamment des droits applicatifs sur `user_sessions`.
Le répartiteur ne crée ni compte ni poste et ne lance pas de migration.

Nginx écoute sur `8080` dans son conteneur, publié sur `8110` sur l'hôte.
Sa configuration source est un template : l'entrypoint de l'image officielle
injecte le résolveur DNS du conteneur au démarrage, sous Docker comme sous Podman.
Les montages sont en lecture seule avec le marquage `Z` pour les hôtes SELinux.
`TRUST_PROXY_HEADERS=1` est configuré pour les applications internes derrière ce
seul proxy. En exécution directe hors Compose, laisser cette variable à `0`.
`SESSION_COOKIE_SECURE=0` permet l'accès HTTP local ; passer à `1` uniquement
avec une terminaison HTTPS correctement configurée. La configuration fournie
n'active pas TLS.

### Vérifications manuelles

Ouvrir chaque environnement et vérifier les ressources CSS/JS, la navigation
sur mobile et les actions HTMX. Avec deux environnements déjà connectés,
changer via le sélecteur : les deux sessions concernées doivent être effacées
et la destination doit exiger une nouvelle connexion. Vérifier également la
révocation du jeton terrain, le rejet d'un `POST` sans CSRF et le parcours sans
JavaScript. En production, contrôler la sélection d'une presse active, la nouvelle
validation opérateur et l'absence de clôture du poste. Aucun test pytest n'est
ajouté pour cette évolution.

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

Lorsqu'une demande est créée ou que son statut change, l'application publie un événement dans un flux Redis commun, par exemple `plasturgie:production:events`. Les services concernés consomment ce flux avec leur propre groupe de consommateurs :

- `plasturgie:manutention` ;
- `plasturgie:qualite` ;
- `plasturgie:techniciens`.

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
REDIS_STREAM=plasturgie:production:events
REDIS_CONSUMER_GROUP=plasturgie:<service>
REDIS_CONSUMER_NAME=<hostname>
```

La migration sera progressive : ajout de Redis, publication depuis la production, ajout des consommateurs métier, puis ajout du rafraîchissement temps réel des écrans. Le rechargement HTMX périodique pourra rester un mécanisme de récupération tant que la reprise sur erreur n'est pas validée.
