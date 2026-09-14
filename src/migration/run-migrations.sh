#!/bin/bash

set -euo pipefail

NETWORK="faiveley_faiv-migrations"
IMAGE="faiveley-migrations"
PROJECT_ROOT="/app"
HOST_PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
    cat <<'EOF'
Usage: ./src/migration/run-migrations.sh <option>

Options:
  --generate  Génère une migration Alembic depuis les modèles SQLAlchemy.
  --run-dry   Génère le SQL d'une mise à niveau dans un fichier, sans modifier la base.
  --apply     Applique les migrations jusqu'à la révision choisie.
  --help      Affiche cette aide.
EOF
}

select_databases() {
    local selection
    PS3="Choisissez les bases à traiter : "
    select selection in "main" "users" "les deux" "annuler"; do
        case "$selection" in
            main)
                DATABASES=("main")
                return
                ;;
            users)
                DATABASES=("users")
                return
                ;;
            "les deux")
                DATABASES=("main" "users")
                return
                ;;
            annuler)
                exit 0
                ;;
            *)
                echo "Sélection invalide."
                ;;
        esac
    done
}

configure_database() {
    local database_type="$1"

    if [[ "$database_type" == "main" ]]; then
        MIGRATION_DIR="$PROJECT_ROOT/main"
        HOST_MIGRATION_DIR="$HOST_PROJECT_ROOT/migration/main"
        DATABASE_NAME_VARIABLE="POSTGRES_DB_MAIN"
    else
        MIGRATION_DIR="$PROJECT_ROOT/users"
        HOST_MIGRATION_DIR="$HOST_PROJECT_ROOT/migration/users"
        DATABASE_NAME_VARIABLE="POSTGRES_DB_USERS"
    fi

    if [[ ! -d "$HOST_MIGRATION_DIR" ]]; then
        echo "Erreur : le répertoire $MIGRATION_DIR n'existe pas."
        exit 1
    fi
}

load_environment() {
    ENV_FILE_HOST="$HOST_PROJECT_ROOT/migration/.env.migr"
    if [[ ! -f "$ENV_FILE_HOST" ]]; then
        echo "Erreur : le fichier $ENV_FILE_HOST n'existe pas."
        exit 1
    fi

    set -a
    source "$ENV_FILE_HOST"
    set +a
    echo "Variables d'environnement chargées depuis $ENV_FILE_HOST."
}

check_container_prerequisites() {
    if ! podman network inspect "$NETWORK" > /dev/null 2>&1; then
        echo "Erreur : le réseau Podman $NETWORK n'existe pas."
        exit 1
    fi

    if ! podman image inspect "$IMAGE" > /dev/null 2>&1; then
        echo "Construction de l'image $IMAGE..."
        podman build \
            -f "$HOST_PROJECT_ROOT/migration/dockerfile.migr" \
            -t "$IMAGE" \
            "$HOST_PROJECT_ROOT"
    fi
}

run_alembic() {
    local command="$1"
    local output_file="${2:-}"
    local migration_volume="$HOST_MIGRATION_DIR:$MIGRATION_DIR:z"
    local output_volume=()

    if [[ -n "$output_file" ]]; then
        output_volume=(-v "$HOST_MIGRATION_DIR/dry-runs:$MIGRATION_DIR/dry-runs:z")
    fi

    podman run --rm \
        --network "$NETWORK" \
        -e "POSTGRES_HOST=${POSTGRES_HOST}" \
        -e "POSTGRES_PORT=${POSTGRES_PORT}" \
        -e "POSTGRES_USER_MIGR=${POSTGRES_USER_MIGR}" \
        -e "POSTGRES_PASSWORD_MIGR=${POSTGRES_PASSWORD_MIGR}" \
        -e "POSTGRES_USER_APP=${POSTGRES_USER_APP}" \
        -e "POSTGRES_DB_MAIN=${POSTGRES_DB_MAIN}" \
        -e "POSTGRES_DB_USERS=${POSTGRES_DB_USERS}" \
        -v "$migration_volume" \
        -v "$HOST_PROJECT_ROOT/common:/app/common:z" \
        "${output_volume[@]}" \
        "$IMAGE" \
        bash -c "alembic -c '$MIGRATION_DIR/alembic.ini' $command${output_file:+ > '$MIGRATION_DIR/dry-runs/$output_file'}"
}

generate_migration() {
    local database_type="$1"
    local migration_name

    configure_database "$database_type"
    read -r -p "Nom de la migration pour $database_type : " migration_name
    if [[ -z "$migration_name" ]]; then
        echo "Erreur : le nom de migration est requis."
        exit 1
    fi
    run_alembic "revision --autogenerate -m '$migration_name'"
}

generate_dry_run() {
    local database_type="$1"
    local timestamp
    local output_file

    configure_database "$database_type"
    mkdir -p "$HOST_MIGRATION_DIR/dry-runs"
    timestamp="$(date +%Y%m%d-%H%M%S)"
    output_file="${timestamp}-upgrade-head.sql"
    run_alembic "upgrade head --sql" "$output_file"
    echo "SQL écrit dans $HOST_MIGRATION_DIR/dry-runs/$output_file."
}

select_revision() {
    local database_type="$1"
    local -a revisions=()
    local revision
    local selected_revision

    configure_database "$database_type"
    mapfile -t revisions < <(
        podman run --rm \
            --network "$NETWORK" \
            -e "POSTGRES_HOST=${POSTGRES_HOST}" \
            -e "POSTGRES_PORT=${POSTGRES_PORT}" \
            -e "POSTGRES_USER_MIGR=${POSTGRES_USER_MIGR}" \
            -e "POSTGRES_PASSWORD_MIGR=${POSTGRES_PASSWORD_MIGR}" \
            -e "POSTGRES_DB_MAIN=${POSTGRES_DB_MAIN}" \
            -e "POSTGRES_DB_USERS=${POSTGRES_DB_USERS}" \
            -v "$HOST_MIGRATION_DIR:$MIGRATION_DIR:z" \
            -v "$HOST_PROJECT_ROOT/common:/app/common:z" \
            "$IMAGE" \
            bash -c "alembic -c '$MIGRATION_DIR/alembic.ini' history --verbose" \
            | awk '/^Rev: / { print $2 }'
    )

    if [[ ${#revisions[@]} -eq 0 ]]; then
        echo "Erreur : aucune migration trouvée pour $database_type."
        exit 1
    fi

    revisions=("${revisions[@]}" "head" "annuler")
    PS3="Révision cible pour $database_type : "
    select selected_revision in "${revisions[@]}"; do
        case "$selected_revision" in
            head)
                SELECTED_REVISION="head"
                return
                ;;
            annuler)
                exit 0
                ;;
            "")
                echo "Sélection invalide."
                ;;
            *)
                SELECTED_REVISION="$selected_revision"
                return
                ;;
        esac
    done
}

apply_migrations() {
    local database_type="$1"

    select_revision "$database_type"
    run_alembic "upgrade $SELECTED_REVISION"
    echo "Migrations appliquées jusqu'à $SELECTED_REVISION pour $database_type."
}

main() {
    local action="${1:---help}"

    case "$action" in
        --generate|--run-dry|--apply)
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            usage
            exit 1
            ;;
    esac

    load_environment
    check_container_prerequisites
    select_databases

    local database_type
    for database_type in "${DATABASES[@]}"; do
        case "$action" in
            --generate)
                generate_migration "$database_type"
                ;;
            --run-dry)
                generate_dry_run "$database_type"
                ;;
            --apply)
                apply_migrations "$database_type"
                ;;
        esac
    done
}

main "$@"