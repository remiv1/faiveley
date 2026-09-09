#!/bin/bash
set -e

INIT_DIR="/docker-entrypoint-initdb.d"

echo "[INFO] Nettoyage des fichiers SQL sensibles..."

# Supprimer uniquement les fichiers générés
find "$INIT_DIR" -maxdepth 1 -type f -name "*.sql" ! -name "*.pattern.sql" -print -delete

echo "[INFO] Nettoyage terminé."
