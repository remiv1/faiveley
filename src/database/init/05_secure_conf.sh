#!/bin/bash
set -e

CONF="$PGDATA/postgresql.conf"

# Forcer SCRAM
sed -i "s/^#\?password_encryption.*/password_encryption = 'scram-sha-256'/" "$CONF"
