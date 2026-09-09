#!/bin/bash

# Script pour générer les fichiers SQL à partir des templates .pattern
# Les variables d'environnement doivent être chargées avant l'exécution

set -e

INIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Vérifier que les variables nécessaires sont définies
required_vars=(
    "POSTGRES_DB_MAIN"
    "POSTGRES_DB_USERS"
    "POSTGRES_USER_APP"
    "POSTGRES_PASSWORD_APP"
    "POSTGRES_USER_SECURE"
    "POSTGRES_PASSWORD_SECURE"
    "POSTGRES_USER_MIGR"
    "POSTGRES_PASSWORD_MIGR"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "Erreur: Variable $var non définie"
        exit 1
    fi
done

# Générer les fichiers SQL à partir des templates
for template in "$INIT_DIR"/*.sql.pattern; do
    if [ -f "$template" ]; then
        output="${template%.pattern}"
        echo "Génération de $output..."
        
        # Remplacer tous les patterns ${VAR} par leurs valeurs
        envsubst < "$template" > "$output"
        chmod 600 "$output"
        echo "✓ $output créé"
    fi
done

echo "✓ Tous les fichiers SQL ont été générés avec succès"