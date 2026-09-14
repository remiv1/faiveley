# Console d'administration du POC FaiveleyTech

Cette console permet de gérer les comptes administrateurs et les paramètres du POC FaiveleyTech.

## Génération du compte administrateur de démonstration

Pour initialiser le compte administrateur de démonstration, exécutez le script `seed_admin.py` :

```bash
podman compose exec dashboard python /app/apis/dashbord/seed_admin.py
```

Le compte créé aura les identifiants suivants :

- **Utilisateur** : `admin`
- **Mot de passe** : `admin`

## Situation actuelle du POC

Le dashboard administre les utilisateurs et les paramètres du POC. Il ne consomme pas actuellement les événements de production et ne participe pas au traitement des demandes opérationnelles.

## Solution retenue pour la production

Le dashboard pourra consulter les données métier et les indicateurs depuis PostgreSQL. Les événements opérationnels resteront distribués aux services concernés par Redis Streams : manutention, qualité et techniciens.

Une intégration temps réel du dashboard pourra être ajoutée ultérieurement si les besoins de supervision le justifient. Elle n'est pas incluse dans le périmètre actuel de la solution retenue.
