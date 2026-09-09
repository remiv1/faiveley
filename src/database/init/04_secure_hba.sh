#!/bin/bash
set -e

HBA="$PGDATA/pg_hba.conf"

# Supprimer les règles trust ou ident
sed -i '/^[[:space:]]*local[[:space:]]\+all[[:space:]]\+all[[:space:]]\+trust/d' "$HBA"
sed -i '/^[[:space:]]*host[[:space:]]\+all[[:space:]]\+all[[:space:]]\+.*trust/d' "$HBA"
sed -i '/^[[:space:]]*local[[:space:]]\+all[[:space:]]\+all[[:space:]]\+ident/d' "$HBA"

# Ajouter la règle locale si absente
if ! grep -q "^local[[:space:]]\+all[[:space:]]\+all" "$HBA"; then
  echo "local   all   all   scram-sha-256" >> "$HBA"
fi

# Ajouter la règle host si absente
if ! grep -q "scram-sha-256" "$HBA"; then
  echo "host    all   all   0.0.0.0/0   scram-sha-256" >> "$HBA"
fi
