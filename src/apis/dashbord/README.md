# Console d'administration du POC FaiveleyTech

Cette console permet de gérer les comptes administrateurs et les paramètres du POC FaiveleyTech.

## Accès et changement d'environnement

Accès via Nginx : `http://localhost:8110/gestion/entree`, puis connexion propre à
la gestion. Le service n'expose plus de port hôte direct.

Le sélecteur est disponible sur l'écran de connexion et dans la navigation.
Changer d'environnement supprime la session locale puis réinitialise celle du
service cible avant sa connexion, par des `POST` protégés par CSRF. Sans JavaScript,
confirmer l'arrivée avec « Continuer ».

Le cookie `dashboard_session` est limité au chemin `/gestion`. Le dashboard
conserve son authentification par cookie Flask signé : supprimer le cookie du
navigateur n'invalide pas côté serveur une copie précédemment récupérée.

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
