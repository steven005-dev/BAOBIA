# Guide commandes BAOBIA

Toutes les commandes sont prévues pour PowerShell depuis la racine du dépôt.

## Démarrage

```powershell
Copy-Item .env.example .env
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..
docker compose up -d
docker compose ps
cd backend
python manage.py migrate
python manage.py runserver
```

Dans un second terminal :

```powershell
cd frontend
npm install
npm run dev
```

## Port PostgreSQL déjà pris

Le port hôte par défaut est `5432`. Pour utiliser `5433`, modifier `.env` :

```text
POSTGRES_PORT=5433
DB_HOST_PORT=5433
```

Le port PostgreSQL interne du conteneur reste `5432`.

## Réinitialiser la base

Cette commande supprime toutes les données PostgreSQL locales :

```powershell
docker compose down -v
docker compose up -d
cd backend
python manage.py migrate
```

`backend/db.sqlite3` n'est plus utilisé. Les secrets restent dans `.env`, jamais dans Git.

## Choix GeoDjango temporaire

GDAL n'étant pas disponible sur Windows dans l'environnement de développement, les
coordonnées sont temporairement stockées dans `latitude`/`longitude` pour toute
l'équipe. Les champs seront migrés vers GeoDjango/PostGIS après décision écrite
et installation commune de GDAL.
