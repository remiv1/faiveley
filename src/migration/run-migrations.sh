#!/bin/bash

# filepath: scripts/run-migrations.sh

set -e

NETWORK="faiveley_faiv-migrations"
IMAGE="faiveley-migrations"

# Obtenir le répertoire racine du projet
PROJECT_ROOT="/app"
HOST_PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Vérifier le paramètre
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "❌ Erreur: Vous devez spécifier 'main' ou 'users' + le nom à donner à la migration"
    echo "Usage: $0 [main|users] <migration_name>"
    exit 1
fi

DB_TYPE="$1"
MIGRATION_NAME="$2"

if [ "$DB_TYPE" != "main" ] && [ "$DB_TYPE" != "users" ]; then
    echo "❌ Erreur: Le paramètre doit être 'main' ou 'users'"
    exit 1
fi

# Chemin vers le fichier .env
ENV_FILE="$PROJECT_ROOT/.env.migr"
ENV_FILE_HOST="$HOST_PROJECT_ROOT/migration/.env.migr"

# Déterminer les variables spécifiques en fonction du type de base de données
if [ "$DB_TYPE" = "main" ]; then
    MIGRATION_DIR="$PROJECT_ROOT/main"
    MIGRATION_DIR_HOST="$HOST_PROJECT_ROOT/migration/main"
    DB_NAME_VAR="POSTGRES_DB_MAIN"
    HOST_MIGRATION_VOLUME="$HOST_PROJECT_ROOT/migration/main:/app/main:z"
else
    MIGRATION_DIR="$PROJECT_ROOT/users"
    MIGRATION_DIR_HOST="$HOST_PROJECT_ROOT/migration/users"
    DB_NAME_VAR="POSTGRES_DB_USERS"
    HOST_MIGRATION_VOLUME="$HOST_PROJECT_ROOT/migration/users:/app/users:z"
fi

# Vérifier que le fichier .env existe
if [ ! -f "$ENV_FILE_HOST" ]; then
    echo "❌ Erreur: Le fichier $ENV_FILE_HOST n'existe pas"
    exit 1
else
    echo "📂 Utilisation du fichier d'environnement: $ENV_FILE"
fi

# Charger les variables d'environnement depuis le fichier .env
set -a
source "$ENV_FILE_HOST"
set +a
echo "✅ Variables d'environnement chargées depuis $ENV_FILE"
echo "📋 Configuration:"
echo "   POSTGRES_HOST=${POSTGRES_HOST}"
echo "   POSTGRES_PORT=${POSTGRES_PORT}"
echo "   POSTGRES_DB_MAIN=${POSTGRES_DB_MAIN}"
echo "   POSTGRES_DB_USERS=${POSTGRES_DB_USERS}"
echo "   POSTGRES_USER_MIGR: [REDACTED]"
echo "   POSTGRES_PASSWORD: [REDACTED]"
echo "   POSTGRES_PASSWORD_MIGR: [REDACTED]"

# Vérifier que le répertoire de migrations existe
if [ ! -d "$MIGRATION_DIR_HOST" ]; then
    echo "❌ Erreur: Le répertoire $MIGRATION_DIR n'existe pas"
    exit 1
else
    echo "📂 Utilisation du répertoire de migrations: $MIGRATION_DIR"
fi

# Vérifier que le réseau existe
if ! podman network inspect $NETWORK > /dev/null 2>&1; then
    echo "❌ Erreur: Le réseau $NETWORK n'existe pas"
    exit 1
else
    echo "🔗 Utilisation du réseau Podman: $NETWORK"
fi

# Vérifier que l'image existe
if ! podman image inspect $IMAGE > /dev/null 2>&1; then
    echo "🔨 Construction de l'image $IMAGE..."
    podman build -f "$HOST_PROJECT_ROOT/migration/dockerfile.migr" -t $IMAGE "$HOST_PROJECT_ROOT"
fi

echo "🚀 Génération des migrations pour la base '$DB_TYPE'..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Lancer le conteneur avec les variables d'environnement du fichier .env
echo "📦 Lancement du conteneur de migrations..."

podman run --rm \
    --network $NETWORK \
    -e "POSTGRES_HOST=${POSTGRES_HOST}" \
    -e "POSTGRES_PORT=${POSTGRES_PORT}" \
    -e "POSTGRES_PASSWORD=${POSTGRES_PASSWORD}" \
    -e "POSTGRES_USER_MIGR=${POSTGRES_USER_MIGR}" \
    -e "POSTGRES_PASSWORD_MIGR=${POSTGRES_PASSWORD_MIGR}" \
    -e "POSTGRES_DB_MAIN=${POSTGRES_DB_MAIN}" \
    -e "POSTGRES_DB_USERS=${POSTGRES_DB_USERS}" \
    -v "$HOST_MIGRATION_VOLUME" \
    -v "$HOST_PROJECT_ROOT/common:/app/common:z" \
    $IMAGE \
    bash -c "
        echo '          +———————————————————————————————————————+'
        echo '          |         Début de la migration         |'
        echo '          +———————————————————————————————————————+'
        echo
        echo '📂 Données SQLAlchemy...'
        ls -l /app/db_models
        alembic -c '$MIGRATION_DIR/alembic.ini' revision --autogenerate -m '$MIGRATION_NAME'
        echo '📂 Migrations générées dans le répertoire:'
        find /app -maxdepth 4 -type d -name versions
        echo '📂 Contenu du répertoire de migrations:'
        ls -al /app/$DB_TYPE/versions
    "

EXIT_CODE=$?

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Migrations générées avec succès pour '$DB_TYPE'!"
else
    echo "❌ Erreur lors de la génération des migrations"
    exit $EXIT_CODE
fi