# API Production

A Créer (Flask)

Cette API doit servir aux opérateurs de production pour gérer les ordres de fabrication de la journée.

Aujourd'hui le système est papier et les opérateurs remplissent manuellement les ordres de fabrication.

Cette API sera servie sur une console tactile industrielle.

Cette API doit permettre de remplir :

- Les pièces réalisées (qté) chaque heure
- Les arrêts de production (durée) et leur cause
- Les rebuts (qté) et leur cause chaque heure
- Les commentaires opérateurs
- Les commentaires techniciens

L'API doit également permettre de demander :

- L'approvisionnement en matières premières
- Le support qualité (HTMX)
- Le support logistique (HTMX)
- La maintenance pour une raison de qualité (HTMX)
- La maintenance pour une raison technique (HTMX)

C'est le manager qui attribue l'OF et le poste de travail à chaque opérateur.

## Dockerfile

A créer

## Endpoints

A créer et à packager en blueprints

- `GET /` : Ecran d'accueil du post de travail
- `POST /check` : Valide la présence de l'opérateur par un code à 4 chiffres
- `POST /pieces` : Enregistrer les pièces réalisées chaque heure (HTMX)
- `POST /arrets` : Enregistrer les arrêts de production et leur cause (HTMX)
- `POST /rebuts` : Enregistrer les rebuts et leur cause chaque heure (HTMX)
- `POST /commentaires-operateurs` : Enregistrer les commentaires des opérateurs (HTMX)
- `POST /commentaires-techniciens` : Enregistrer les commentaires des techniciens (HTMX)
- `GET /approvisionnement` : Voir la liste des matériels, des appro demandés et les status.
- `POST /appro` : Demander l'approvisionnement en matières premières (HTMX)
- `POST /appro/escalade` : Escalader une demande d'approvisionnement (HTMX) [normal → urgent → rupture]
- `POST /support/qualite` : Demander le support qualité (HTMX)
- `POST /support/logistique` : Demander le support logistique (HTMX)
- `POST /maintenance/qualite` : Demander la maintenance pour une raison de qualité (HTMX)
- `POST /maintenance/technique` : Demander la maintenance pour une raison technique (HTMX)

## UX/UI

Les écrans sont volontairement simples et épurés pour faciliter l'utilisation sur une console tactile industrielle avec des gants.
Les boutons sont grands et espacés pour éviter les erreurs de saisie.
Les informations essentielles sont mises en avant, tandis que les détails secondaires sont accessibles via des menus ou des pop-ups.
Une action = 1 écran.
Les écrans doivent être réactifs et fournir un retour immédiat à l'utilisateur après chaque action.

## Configuration

L'API est exposée sous le préfixe `/production`. Chaque console ouvre sa page avec
`GET /production/<press_ref>`. Le serveur associe alors la session HTTP au poste actif
dont `press_ref` correspond à l'URL.

Chaque requête métier transmet `id_post`. Le serveur refuse la requête si cet identifiant
ne correspond pas à celui enregistré dans la session de la console.

Les variables d'environnement suivantes sont obligatoires :

- `FLASK_SECRET_KEY` : clé de signature des sessions Flask.
- `POSTGRES_USER_APP`, `POSTGRES_PASSWORD_APP` et `POSTGRES_DB_MAIN` : paramètres de connexion à la base métier.

Dans Compose, la connexion vise `db-main:5432`, le nom DNS interne du conteneur
PostgreSQL sur le réseau `faiv-network`. L'API n'accède donc pas à PostgreSQL par le
port exposé de la machine hôte. `DATABASE_URL` peut être défini pour surcharger cette
configuration dans un environnement de développement ou de test.

Le conteneur exécute Flask via Gunicorn, avec le worker synchrone multi-thread
`gthread`. Les paramètres suivants sont configurables dans l'environnement Compose :

- `GUNICORN_WORKERS` : nombre de processus Gunicorn, `2` par défaut.
- `GUNICORN_THREADS` : nombre de threads par processus, `4` par défaut.
- `GUNICORN_TIMEOUT` : délai maximal d'une requête, `30` secondes par défaut.
- `GUNICORN_MAX_REQUESTS` : nombre maximal de requêtes avant le renouvellement d'un worker, `1000` par défaut.
- `GUNICORN_MAX_REQUESTS_JITTER` : variation aléatoire du renouvellement, `100` par défaut.

Les requêtes `POST` doivent fournir le jeton CSRF de la session dans l'en-tête
`X-CSRFToken`. La page d'accueil le transmet automatiquement avec HTMX.

## Modèle de données

- `Posts.press_ref` identifie la presse de la console.
- `PostHours` contient un cumul par poste et par heure UTC, unique pour le couple `id_post` et `recorded_at`.
- `ProductionComments` regroupe les commentaires opérateurs et techniciens avec `author_type`.
- Les demandes d'approvisionnement sont liées au poste et au matériel demandé. L'API refuse un matériel qui n'est pas associé à l'OF du poste.
