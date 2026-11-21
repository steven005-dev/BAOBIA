# BAOBIA : script de démonstration (SELAB 2026)

> Pour la personne qui présente et pour la répétition générale du samedi 21 novembre (présentation le dimanche 22).
> Toutes les données sont **simulées**. BAOBIA n'a **aucune valeur légale**.
> Les étapes marquées ⏳ dépendent de modules encore en cours : mettre ce fichier à jour à la répétition.

## 1. Préparer (la veille)

| # | Action | Commande / détail |
|---|---|---|
| 1 | Base propre avec les données de démo | `docker compose down -v` ; `docker compose up -d` ; dans `backend/` : `python manage.py migrate` puis `python manage.py seed --demo` (`SEED_DEMO_PASSWORD` dans `.env` ; charge aussi les districts et régions de Côte d'Ivoire et place les élevages de démo dans le Poro et le Gbêkê) |
| 2 | Certificat HTTPS (caméra du téléphone) | dans `frontend/` : `npm run cert` |
| 3 | Serveurs | `python manage.py runserver` (backend) ; `npm run dev:phone` (frontend) |
| 4 | Téléphones | même Wi-Fi que le PC ; ouvrir `https://<IP-du-PC>:5173`, accepter l'avertissement une fois, autoriser la caméra |
| 5 | Étiquettes du scan | imprimer les QR codes des animaux déjà étiquetés (section 3 ; un QR = le code seul, 9 caractères), les coller sur des cartons. Pour un animal ajouté en direct, son code s'affiche sur sa fiche |
| 6 | Secours | vidéo du parcours et maquette 3D (Yéné) prêtes sur le PC, hors ligne |

Le jour J, refaire seulement 3 et 4. **Ne pas relancer le `seed` en public** (il ne recrée rien si les données existent, mais inutile de prendre le risque).

## 2. Comptes (mot de passe = `SEED_DEMO_PASSWORD`)

| Rôle | Numéro à saisir | Élevages / périmètre |
|---|---|---|
| Éleveur 1 | `00 00 00 00 01` | Élevage A (Zone Nord), détenteur |
| Éleveur 2 | `00 00 00 00 02` | Élevage B (Zone Nord), co-détenteur de A |
| Éleveur 3 | `00 00 00 00 03` | Élevage C et Marché (Zone Sud) |
| Vétérinaire | `00 00 00 00 04` | tout le pays de démo, habilitation valide |
| Agent de terrain | `00 00 00 00 05` | Zone Nord, mandat sur l'Élevage B |
| Autorité | `00 00 00 00 06` | tout le pays de démo |

Administration Django (équipe technique seulement) : `/admin/`, compte créé avec `python manage.py createsuperuser`.

## 3. Étiquettes de démonstration

| Code | Où |
|---|---|
| `KECT T2U8 V` · `MYLH HLPG V` · `82MR XN5S Y` · `E8AQ B29Z 6` | posées : animaux 1 à 4, Élevage A (3 bovins, 1 porc) |
| `XT5A H86V 9` · `5ZGQ Y7M4 6` · `QGKQ U8G4 S` | posées : animaux 5 à 7, Élevage B (2 bovins, 1 chèvre) |
| `ZSQE 4QYM G` | posée : animal 8, Élevage C (mouton) |

**Boucles préimprimées (voie principale, spec v1.4).** À « Ajouter un animal », dernière étape **Quelle étiquette ?** → **Scanner la boucle** : scanner le QR de la boucle ou saisir son code. Le serveur accepte une boucle remise à cet élevage (ou jamais remise), pas encore posée.

- Base de démo actuelle (20/11) : 4 boucles remises à l'élevage de l'Éleveur 1 : `7DSJ VLHQ J` · `KPJK SH4C 7` · `LSZ9 P598 4` · `WSQP 73YM 8`.
- Base recréée par `seed --demo` : 2 boucles vierges remises à l'Élevage A et 2 à l'Élevage B (codes 9 à 12 du lot de démo).
- Pour la scène, imprimer leurs QR à l'avance (n'importe quel générateur de QR : le QR ne contient que le code).

**Secours :** **Pas de boucle : créer un code** → le téléphone crée le code et la fiche l'affiche en grand, avec **Imprimer**.

## 4. Le parcours (≈ 7 minutes)

**Message d'ouverture (30 s).** « Quand une maladie apparaît dans un élevage, il faut retrouver vite les autres élevages qui ont reçu ses animaux. Aujourd'hui, personne ne le sait. BAOBIA rend ce chemin retrouvable, simplement, même sans réseau. »

| # | Qui (téléphone) | Action | Ce qu'on montre | État |
|---|---|---|---|---|
| 0 | Agent de terrain | Accueil → **Inscrire** → nom, numéro, élevage, zone (Nord), espèces → **cocher l'accord de l'éleveur** → Inscrire | pas d'inscription libre ; sans l'accord (loi 2013-450), l'inscription est refusée : l'agent crée le compte en face de l'éleveur ; **le mot de passe (8 chiffres) est créé par le téléphone** et affiché pour être remis ; puis **Ajouter ses animaux** (mandat de l'agent) ; l'éleveur se connecte avec ce numéro et ce mot de passe | ✅ |
| 1 | Éleveur 1 | Accueil → **Ajouter** → Bovin → Ajouter | une question par écran, gros boutons, « Animal ajouté. » ; **le code de l'étiquette est créé automatiquement** ; la fiche montre l'étiquette (QR + code) et le bouton **Imprimer** | ✅ |
| 2 | Éleveur 1 | **Scanner** l'étiquette `KECT T2U8 V` | « Animal retrouvé. », fiche ; le scan est enregistré (heure, position si autorisée) | ✅ |
| 3 | Éleveur 3 | **Scanner** la même étiquette | vue réduite : l'espèce seulement, **aucun nom d'élevage** (confidentialité) | ✅ |
| 4 | Éleveur 1 → Éleveur 2 | **Transférer** un animal, puis **Recevoir** et confirmer avec le code | double confirmation, l'animal change d'élevage ; sans réseau, l'envoi attend dans la file et part au retour du réseau | ✅ |
| 5 | Éleveur 2 | **Signaler** un cas : une question par écran, symptômes en icônes, **combien de morts**, puis **combien de malades** | « Signalement envoyé au vétérinaire. » ; ensuite la fiche de l'animal montre sa partie **Santé** (signalement en cours) | ✅ écran fait (Yéo), à vérifier en répétition |
| 6 | Vétérinaire | **Valider** ; voir les élevages exposés, le chemin et le **cas négatif** | l'alerte s'explique (chemin, élevages écartés, transfert déclaré d'un seul côté) ; seul le vétérinaire habilité valide | ✅ écrans faits (Yéo), à vérifier en répétition |
| 7 | Éleveur exposé | Accueil : message « Un animal arrivé chez vous a peut-être été en contact avec un cas suspect. Appelez votre vétérinaire. » | message neutre, sans l'élevage d'origine | ✅ affichage prêt, ⏳ déclenchement par l'alerte |
| 8 | Autorité | **Carte** : zones normal / à surveiller / contact possible / alerte / pas assez de données | **carte de Côte d'Ivoire** : 14 districts colorés, toucher un district = zoom sur ses régions ; points des élevages (vétérinaire et Autorité seulement), aucun nom ; marche hors ligne (tracés dans l'application) | ✅ écran fait (Yéo), à vérifier en répétition |

Bonus si le temps le permet : sur la fiche de l'animal ajouté à l'étape 1, **Changer l'étiquette** → « Abîmée » → un nouveau code est créé ; scanner l'ancien code renvoie « Étiquette remplacée » vers le même animal.

Bonus 2 : l'éleveur inscrit à l'étape 0 se connecte avec le mot de passe remis par l'agent, puis Accueil → **Changer mon mot de passe** (l'actuel, puis un nouveau d'au moins 8 caractères).

**Second scénario (si demandé) : regroupement de zone.** Plusieurs signalements similaires dans une zone → les vétérinaires de la zone sont prévenus → l'un confirme ou infirme. Règles explicables, pas d'IA qui diagnostique. ⏳ Yéo.

## 5. Phrases à dire (et à ne jamais dire)

- « **Exposé** » ou « **contact possible** », **jamais** « contaminé ».
- « Le système **propose**, le **vétérinaire habilité décide**. »
- « Le QR code ne contient **que le numéro** : aucune donnée personnelle ni sanitaire. »
- « Pas de suivi en continu : la position n'est notée **qu'au moment d'un scan**. »
- « Prototype, **données simulées**, **aucune valeur légale**. »

## 6. Plan de secours

| Problème | Réaction immédiate |
|---|---|
| Caméra refusée ou lente | saisir le code à la main (champ sous la caméra) : c'est prévu pour le terrain |
| Avertissement HTTPS sur le téléphone | « Paramètres avancés » → « Continuer » (certificat local de démo) |
| Wi-Fi de la salle instable | partage de connexion d'un téléphone pour le PC et les autres téléphones |
| Un écran ⏳ n'est pas prêt | montrer la vidéo ou la maquette 3D pour cette étape, puis reprendre en direct |
| Session expirée | se reconnecter (numéro + mot de passe), les données restent sur le serveur |
| Tout plante | vidéo complète du parcours |

## 7. Répétition du samedi 21 novembre

- Chronométrer chaque étape ; viser 7 minutes, questions comprises 10.
- Faire le parcours **deux fois** sur les vrais téléphones.
- Hors ligne : la file d'envoi de Romuald est branchée pour les **mouvements** (Transférer, Recevoir). Pour les autres actions (ex. Ajouter un animal), sans réseau l'écran affiche « Pas de connexion » et rien n'est gardé : ne montrer le hors-ligne que sur un transfert.
- Base : la base tourne dans **Docker** (port 5433 sur ce PC). Lancer Docker Desktop avant `docker compose up -d`.
- Mettre à jour la colonne « État » de la section 4 et retirer ce qui n'est pas prêt.
