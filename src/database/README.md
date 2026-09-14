# Base de données

## Rôle

Le service `db-main` fournit l'instance PostgreSQL utilisée par le POC. Il
persiste les données dans le volume Docker `faiv-db-data` et rejoint les
réseaux `faiv-network`, `faiv-secure` et `faiv-migrations`.

L'image est construite depuis `dockerfile.postgres`, basé sur
`postgres:18-bookworm`. Elle initialise PostgreSQL en UTF-8 avec la locale
française `fr_FR.utf8`.

## Initialisation

Au moment de construire l'image, le Dockerfile charge `.env.postgres` puis exécute `init/00_generate_models.sh`. Ce script vérifie les variables requises et transforme les fichiers `*.sql.pattern` en fichiers SQL exécutables avec `envsubst`.

Les scripts générés sont exécutés lors de la première initialisation du volume PostgreSQL, dans l'ordre de leur préfixe numérique :

- `01_db_build.sql.pattern` crée les bases, rôles et schémas ;
- `02_create_users.sql.pattern` attribue les droits aux utilisateurs ;
- `03_create_extensions.sql.pattern` crée les extensions nécessaires ;
- `04_secure_hba.sh` configure l'authentification réseau ;
- `05_secure_conf.sh` applique la configuration PostgreSQL ;
- `99_cleanup.sh` nettoie les fichiers temporaires.

Les scripts d'initialisation ne sont pas rejoués tant que le volume `faiv-db-data` existe. Toute modification de leur contenu doit donc être traitée par une migration pour une base déjà initialisée.

## Bases et schémas

La configuration crée deux bases distinctes :

- `POSTGRES_DB_MAIN`, pour les données applicatives, avec les schémas `app_schema` et `migr_main` ;
- `POSTGRES_DB_USERS`, pour les comptes et sessions, avec les schémas `auth_schema` et `migr_users`.

Le `search_path` par défaut de chaque base privilégie son schéma métier, puis `public`.

Les services applicatifs utilisent `POSTGRES_USER_APP`. Les migrations utilisent l'utilisateur séparé `POSTGRES_USER_MIGR`, propriétaire des schémas de migration. Les comptes et secrets sont définis dans `.env.postgres`, qui ne doit pas être versionné ni diffusé.

## Accès applicatif

Les applications conteneurisées se connectent au nom DNS interne `db-main` sur le port `5432`. Elles ne passent pas par un port exposé par la machine hôte. La connexion est construite avec les variables `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER_APP`, `POSTGRES_PASSWORD_APP` et le nom de la base cible.

Les modèles SQLAlchemy se trouvent dans `src/common/models`. Les évolutions de ces modèles sont appliquées aux bases existantes via Alembic ; voir le [README](src/migration) du dossier `src/migration`.
