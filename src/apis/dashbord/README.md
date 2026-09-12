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
