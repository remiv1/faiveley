# Migrations de base de données

## Rôle

Les migrations Alembic font évoluer les deux bases PostgreSQL déjà initialisées :

- `main`, dont les scripts et révisions se trouvent dans `main` ;
- `users`, dont les scripts et révisions se trouvent dans `users`.

Les modèles SQLAlchemy utilisés pour l'autogénération sont partagés dans `src/common/models`.

## Script d'exécution

Le script `run-migrations.sh` est le point d'entrée pour générer, prévisualiser et appliquer les migrations :

```bash
./src/migration/run-migrations.sh --generate
./src/migration/run-migrations.sh --run-dry
./src/migration/run-migrations.sh --apply
```

Après le choix de l'action, le script charge les variables de `src/migration/.env.migr`, puis demande la base à traiter : `main`, `users` ou les deux.

`--generate` demande un nom de migration et exécute `alembic revision --autogenerate`. La révision est créée dans le dossier `versions` de la base sélectionnée.

`--run-dry` exécute `alembic upgrade head --sql` sans modifier PostgreSQL. Le SQL obtenu est écrit dans `dry-runs/<horodatage>-upgrade-head.sql` pour revue.

`--apply` lit l'historique Alembic, propose une révision cible puis exécute `alembic upgrade <revision>`. L'option `head` applique toutes les migrations disponibles.

## Conteneur éphémère et réseau

Le script exécute Alembic dans un conteneur Podman éphémère, supprimé après chaque commande par l'option `--rm`. Il utilise l'image `faiveley-migrations`. Si elle n'existe pas, le script la construit depuis `dockerfile.migr` et `requirements.migr.txt`.

Ce conteneur est relié au réseau Podman `faiveley_faiv-migrations`. Le réseau doit exister avant l'exécution ; il permet au conteneur de joindre PostgreSQL sans exposer la base au poste hôte.

Les dossiers de migration choisis et `src/common` sont montés dans le conteneur. Les fichiers de révision générés sont donc écrits directement dans le répertoire de travail local.

## Utilisateur de migration

Alembic n'utilise pas le compte applicatif. Le script transmet `POSTGRES_USER_MIGR` et `POSTGRES_PASSWORD_MIGR`, en plus des noms des bases et des paramètres d'hôte. Cet utilisateur est dédié aux évolutions de schéma et possède les schémas `migr_main` et `migr_users`.

Les variables attendues sont chargées depuis `.env.migr` :

```text
POSTGRES_HOST
POSTGRES_PORT
POSTGRES_USER_MIGR
POSTGRES_PASSWORD_MIGR
POSTGRES_DB_MAIN
POSTGRES_DB_USERS
```

## Procédure recommandée

1. Modifier les modèles dans `src/common/models`.
2. Générer la migration pour la base concernée.
3. Relire le fichier créé dans `versions`.
4. Produire un `--run-dry` et relire le SQL.
5. Appliquer la révision choisie avec `--apply`.

Une révision appliquée en environnement partagé ne doit pas être modifiée. Une correction doit être portée par une nouvelle migration.
