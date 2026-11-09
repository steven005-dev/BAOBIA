# BAOBIA : guide des commandes essentielles

Pour toute l'équipe, sous **Windows avec PowerShell**. Ouvrez le terminal dans le dossier du projet (`baobia/`) sauf indication contraire.

> Règle d'or : si une commande vous inquiète, **demandez avant** de la lancer. Les commandes de la section « À ne jamais faire » peuvent détruire du travail.

---

## 1. Première installation (une seule fois)

### 1.1 Outils à avoir
```powershell
git --version
python --version     # 3.11 ou plus récent
node --version       # 22 ou plus récent
```
Chacune doit afficher un numéro de version.

### 1.2 Récupérer le projet
```powershell
git clone https://github.com/ORGANISATION/baobia.git
cd baobia
```
(Remplacez l'adresse par celle du dépôt.)

### 1.3 Configurer les secrets locaux
```powershell
Copy-Item .env.example .env
```
Le fichier `.env` reste **sur votre ordinateur**. Il n'est jamais envoyé sur GitHub.

### 1.4 Installer le backend (Django)
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
cd ..
```
Si PowerShell refuse d'activer l'environnement, tapez d'abord :
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
Quand l'environnement est actif, `(.venv)` apparaît au début de la ligne.

### 1.5 Installer le frontend (React)
```powershell
cd frontend
npm install
cd ..
```

---

## 2. Lancer le projet au quotidien

### Backend (un premier terminal)
```powershell
cd backend
.venv\Scripts\Activate.ps1
python manage.py runserver
```
Adresse : http://127.0.0.1:8000

### Frontend (un second terminal)
```powershell
cd frontend
npm run dev
```
Adresse : http://localhost:5173

Pour arrêter un serveur : **Ctrl + C** dans son terminal.

### Base de données PostgreSQL
```powershell
docker compose up -d
docker compose ps
docker compose logs db
docker compose down
```
Docker Desktop doit être ouvert. Le service `db` doit afficher `healthy` avant de lancer Django.

Si le port 5432 est déjà pris :
```powershell
Get-NetTCPConnection -LocalPort 5432 -ErrorAction SilentlyContinue
docker compose down
```
Arrêtez le service qui utilise ce port, ou définissez `DB_HOST_PORT=5433` et `POSTGRES_PORT=5433` dans `.env` (le port interne du conteneur reste `5432`).

Pour repartir sur une base vierge (supprime toutes les données locales) :
```powershell
docker compose down -v
docker compose up -d
cd backend
python manage.py migrate
cd ..
```
Le fichier `backend/db.sqlite3` historique n'est plus utilisé. GeoDjango n'est pas activé : si `gdalinfo --version` échoue sous Windows, le projet reste volontairement sur le backend PostgreSQL standard.

---

## 3. Git : le cycle de travail de tous les jours

### 3.1 Commencer une tâche
```powershell
git switch main
git pull
git switch -c feature/<module>-<sujet>
```
Exemples de noms de branche : `feature/identity-animal-model`, `feature/movements-confirmation`, `feature/health-report-form`.

### 3.2 Voir où l'on en est
```powershell
git status          # quels fichiers ont changé
git branch          # sur quelle branche je suis
git log --oneline -10    # les 10 derniers commits
```

### 3.3 Enregistrer son travail (commit)
```powershell
git status                        # vérifier ce qui sera enregistré
git add .
git commit -m "identity: ajoute le modèle Animal"
```
Format du message : `module: ce qui a été fait`. Pas de « modif » ni de « test ».

### 3.4 Envoyer sur GitHub
```powershell
git push -u origin feature/<module>-<sujet>
```
(Le `-u` n'est utile que la première fois pour cette branche ; ensuite, `git push` suffit.)

Puis, sur GitHub, ouvrez une **demande de fusion** (Pull request) vers `main` (bouton « Compare & pull request »).

### 3.5 Mettre sa branche à jour avec `main`
À faire **avant** d'ouvrir une demande de fusion, et au moins une fois par jour :
```powershell
git switch main
git pull
git switch feature/<module>-<sujet>
git merge main
```
Si Git signale un **conflit**, voir la section 5.

### 3.6 Changer de branche
```powershell
git switch <nom-de-la-branche>
```
Si Git refuse parce que vous avez des changements non enregistrés : faites un commit, ou `git stash` (met le travail de côté) puis, plus tard, `git stash pop`.

### 3.7 Annuler une erreur
```powershell
git restore <fichier>              # abandonne les changements d'un fichier (non enregistrés)
git restore --staged <fichier>     # retire un fichier de l'envoi préparé (garde les changements)
```
**Attention** : `git restore <fichier>` supprime définitivement les changements de ce fichier.

---

## 4. Django

À lancer dans `backend/`, avec `(.venv)` actif.

| Besoin | Commande |
|---|---|
| Vérifier que tout est correct | `python manage.py check` |
| Créer les migrations d'un module | `python manage.py makemigrations identity` |
| Appliquer les migrations | `python manage.py migrate` |
| Créer un administrateur local | `python manage.py createsuperuser` |
| Lancer les tests | `python manage.py test` |
| Ajouter une bibliothèque Python | `pip install <nom>` puis `pip freeze \| Out-File -Encoding ascii requirements.txt` |

**Migrations** : **chaque personne ne crée des migrations que pour ses propres applications.** Si vous changez un modèle, lancez `makemigrations` pour votre module seulement, vérifiez le fichier créé, et envoyez-le avec votre code.

---

## 5. Résoudre un conflit Git

Un conflit arrive quand deux personnes ont modifié les mêmes lignes. Il n'est pas grave.

1. `git status` indique les fichiers « both modified ».
2. Ouvrez chaque fichier dans VS Code : vous voyez des marques `<<<<<<<`, `=======`, `>>>>>>>`. VS Code propose des boutons « Accepter le changement actuel / entrant / les deux ».
3. Gardez le bon contenu, supprimez les marques.
4. Enregistrez, puis :
```powershell
git add <fichier>
git commit
```
5. En cas de doute sur le contenu à garder, **demandez à la personne concernée** : ne choisissez pas au hasard.

---

## 6. Frontend

À lancer dans `frontend/`.

| Besoin | Commande |
|---|---|
| Installer les dépendances | `npm install` |
| Lancer en développement | `npm run dev` |
| Vérifier le style du code | `npm run lint` |
| Construire pour la production | `npm run build` |
| Ajouter une bibliothèque | `npm install <nom>` |

Après un `git pull`, si `package.json` a changé, relancez `npm install`. Si `requirements.txt` a changé, relancez `pip install -r requirements.txt`.

---

## 7. Problèmes fréquents

| Message ou symptôme | Cause et solution |
|---|---|
| `ENOSPC: no space left on device` | Le disque est plein. Libérer de la place (nettoyage de disque, `npm cache clean --force`) puis relancer. |
| « L'exécution de scripts est désactivée » | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, puis relancer l'activation. |
| `python` ou `pip` introuvable | L'environnement n'est pas actif : `.venv\Scripts\Activate.ps1` dans `backend/`. |
| `ModuleNotFoundError` | Dépendance manquante : `pip install -r requirements.txt`. |
| Port 8000 ou 5173 déjà utilisé | Un ancien serveur tourne encore : le fermer (Ctrl + C) ou relancer le terminal. |
| `git push` refusé | Quelqu'un a envoyé avant vous : `git pull` ou `git merge main`, puis renvoyer. |
| Deux migrations en conflit | Ne les modifiez pas à la main : prévenez le chef de projet. |
| `.env` absent | `Copy-Item .env.example .env`. |

---

## 8. À ne jamais faire

- **Ne jamais** `git push --force` (surtout sur `main`).
- **Ne jamais** `git reset --hard` ni supprimer un dossier de `.git` sans demander.
- **Ne jamais** envoyer `.env`, des mots de passe, des clés, des données réelles.
- **Ne jamais** pousser directement sur `main` : toujours par une demande de fusion.
- **Ne jamais** modifier les modèles ou les migrations d'un module qui n'est pas le vôtre sans prévenir son responsable.
- **Ne jamais** commiter `node_modules/`, `.venv/` ou de gros fichiers (vidéos, modèles 3D).