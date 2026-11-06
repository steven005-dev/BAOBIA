# BAOBIA : lignes directrices de l'interface (UI/UX)

> **Mot d'ordre : la simplicité.** Quand un choix oppose le joli à l'évident, on choisit l'évident. Public : éleveurs et agents peu lettrés, téléphone Android modeste, plein soleil, connexion instable.

Version 1.1, 6 novembre 2026. Référence pour toute l'équipe, y compris la maquette 3D. **Source de vérité des valeurs : le fichier de thème CSS (section 12).** En cas d'écart, le code fait foi, puis on corrige ce document.

Pile : React, Vite, TypeScript, Tailwind CSS v4, shadcn/ui personnalisé, lucide-react.

## 1. Principes

1. **Une action principale par écran.** Elle est visible, nommée et accompagnée d'une icône.
2. **Icône et mot.** Jamais l'icône seule, jamais le mot seul.
3. **La couleur ne porte jamais le sens seule.** Toujours une icône et un mot ; sur la carte, un motif et un contour en plus.
4. **Commandes généreuses.** Zone tactile d'au moins 48 px ; bouton principal de 60 px.
5. **Peu de texte.** Une phrase = une information ; français simple ; un seul mot par action dans toute l'application.
6. **Choisir plutôt que taper.** Boutons, icônes, listes, + et - ; le clavier en dernier recours.
7. **Retour immédiat.** Chaque action montre son résultat ; les erreurs disent quoi faire.
8. **Hors ligne visible.** L'état de connexion et d'envoi est toujours affiché.
9. **Pas de menu caché.** 4 entrées de navigation au plus, toujours visibles.
10. **Place pour l'aide audio.** Prévue dans l'en-tête de chaque écran.

**Règle sanitaire :** une zone « exposée » n'est jamais « contaminée ». Le rouge correspond uniquement à une alerte validée par un vétérinaire.

## 2. Couleurs

| Rôle | Variable | Hex | Usage |
|---|---|---|---|
| Marque | --brand | #174A3B | Bouton principal, en-tête, éléments de navigation actifs |
| Marque, survol | --brand-hover | #123D31 | Bouton principal appuyé |
| Marque claire | --brand-light | #E8F0EC | Fonds d'accent, élément sélectionné |
| Fond | --background | #F7F8F5 | Fond de page |
| Surface | --surface | #FFFFFF | Cartes, champs, fenêtres |
| Surface 2 | --surface-secondary | #EEF1ED | Zones secondaires, lignes alternées |
| Texte | --foreground | #17231B | Texte principal |
| Texte secondaire | --text-secondary | #59665D | Aides, légendes |
| Bordure | --border | #D5DDD6 | Séparations, contours de champs |
| Focus | --focus | #175CD3 | Contour de focus, liens, information |

### États sanitaires (communs à l'application, la carte et la maquette 3D ; ne pas modifier)

| État | Fond | Texte | Contour | Icône | Motif sur la carte |
|---|---|---|---|---|---|
| Normal | #287A45 | #FFFFFF | #1B5A33 | ShieldCheck | uni |
| À surveiller | #F7DC6F | #302500 | #8A6A00 | Eye | lignes horizontales fines |
| Contact possible | #E8740C | #2B1600 | #9A4A05 | TriangleAlert | diagonales |
| Alerte validée | #B42318 | #FFFFFF | #7F1A12 | Siren | quadrillé serré |
| Pas assez de données | #667085 | #FFFFFF | #475467 | CircleHelp | points |

### Fonctionnelles

| Usage | Couleur | Fond | Icône |
|---|---|---|---|
| Succès | #176B3A | #EAF5ED | CircleCheck |
| Erreur | #9C2A56 | #FDEAF1 | CircleX |
| Information | #175CD3 | #EAF2FC | Info |
| Avertissement (texte) | #8A4B08 | #FFF4DF | TriangleAlert |

**Règles d'usage :**

- Le rouge #B42318 est réservé à l'alerte validée. Les erreurs de saisie utilisent la couleur d'erreur et un message encadré avec icône, jamais une pastille.
- Jaune et orange sanitaires ne servent qu'aux états sanitaires, jamais aux avertissements de l'interface.
- Sur la carte et les badges, chaque état a un contour sombre, une icône et un motif en plus de la couleur.
- Pas de couleur écrite à la main dans les composants : uniquement les variables.

### Contrastes vérifiés (calcul WCAG)

| Combinaison | Ratio | Seuil |
|---|---|---|
| Texte / fond | 15.24:1 | 4,5:1 |
| Texte secondaire / fond | 5.66:1 | 4,5:1 |
| Blanc / marque | 10.10:1 | 4,5:1 |
| Blanc / Normal | 5.30:1 | 4,5:1 |
| Texte sombre / À surveiller | 11.09:1 | 4,5:1 |
| Texte sombre / Contact possible | 5.70:1 | 4,5:1 |
| Blanc / Alerte validée | 6.57:1 | 4,5:1 |
| Blanc / Pas assez de données | 4.97:1 | 4,5:1 |
| Succès / fond succès | 5.87:1 | 4,5:1 |
| Erreur / fond erreur | 6.33:1 | 4,5:1 |
| Information / fond information | 5.30:1 | 4,5:1 |
| Avertissement / fond avertissement | 6.23:1 | 4,5:1 |
| Contour Normal / fond de page | 7.70:1 | 3:1 |
| Contour À surveiller / fond de page | 4.76:1 | 3:1 |
| Contour Contact possible / fond de page | 5.87:1 | 3:1 |
| Contour Alerte / fond de page | 9.57:1 | 3:1 |
| Contour Pas assez de données / fond de page | 7.21:1 | 3:1 |
| Focus / fond de page | 5.62:1 | 3:1 |

Un test sur téléphone réel, en plein soleil, reste nécessaire.

## 3. Typographie

Police : **Atkinson Hyperlegible** (licence SIL OFL 1.1), embarquée dans l'application (`public/fonts/`, fichiers Regular et Bold, plus le fichier de licence). Aucun chargement depuis Google Fonts ou un CDN. Poids 400 et 700 uniquement.

| Élément | Taille | Poids | Interligne |
|---|---|---|---|
| Grand titre | 32 px | 700 | 1,2 |
| Titre de page | 28 px | 700 | 1,2 |
| Sous-titre | 22 px | 700 | 1,3 |
| Titre de carte | 20 px | 700 | 1,3 |
| Texte principal | 18 px | 400 | 1,5 |
| Texte secondaire | 16 px | 400 | 1,5 |
| Légende | 14 px | 700 | 1,4 |
| Bouton | 18 px | 700 | 1,2 |
| Chiffre important | 32 à 40 px | 700 | 1,1 |

Pas de texte fonctionnel sous 14 px ; champs de saisie à 16 px au moins ; éviter les majuscules en continu et les paragraphes longs.

## 4. Espacements, formes, mise en page

| Variable | Valeur | Usage |
|---|---|---|
| space-1 | 4 px | Micro-écart |
| space-2 | 8 px | Éléments proches |
| space-3 | 12 px | Écart entre commandes |
| space-4 | 16 px | Marge mobile, remplissage standard |
| space-5 | 20 px | Groupes |
| space-6 | 24 px | Séparation de sections |
| space-8 | 32 px | Sections principales |
| space-12 | 48 px | Zones de respiration |

| Zones tactiles | Valeur |
|---|---|
| Minimum absolu | 48 x 48 px |
| Bouton secondaire | 52 px de haut |
| Bouton principal | 56 à 60 px de haut |
| Navigation basse | 64 à 72 px de haut |
| Icône de bouton | 24 px |
| Écart entre actions | 12 px minimum |

| Formes | Valeur |
|---|---|
| Petit élément | 8 px |
| Champ et bouton | 12 px |
| Carte | 16 px |
| Fenêtre | 20 px |
| Badge | pastille complète |
| Bordure normale, active, focus | 1 px, 2 px, 3 px |
| Ombre carte | 0 2px 8px rgba(23,35,27,0.08) |
| Ombre fenêtre | 0 8px 24px rgba(23,35,27,0.16) |

**Mobile :** largeur de référence 360 à 430 px ; marges de 16 px ; une colonne ; navigation basse fixe ; en-tête compact (marque, état réseau, place de l'aide audio) ; l'action principale n'est jamais masquée par la navigation.

**Ordinateur :** barre latérale de 240 px ; marges de contenu de 32 px ; formulaires d'environ 720 px de large. Les écrans vétérinaire et administration peuvent être plus denses, avec les mêmes couleurs, icônes et mots.

## 5. Icônes

Bibliothèque **lucide-react**, trait de 2 px, importées dans le code (aucune requête externe). Tailles : navigation et boutons 24 px, badges 18 px, petits indicateurs 16 px, écrans vides 48 px. **Jamais une icône seule.** Vérifier les noms dans la version installée (certains ont été renommés).

| Notion | Icône Lucide | Libellé |
|---|---|---|
| Accueil | House | Accueil |
| Animal | PawPrint* | Animal |
| Troupeau, lot | Users* | Lot |
| Élevage | Warehouse | Élevage |
| Étiquette QR | QrCode | Étiquette |
| Scanner | ScanQrCode | Scanner |
| Ajouter | CirclePlus | Ajouter |
| Modifier | Pencil | Modifier |
| Supprimer | Trash2 | Supprimer |
| Transférer | ArrowLeftRight | Transférer |
| Recevoir | PackageCheck | Recevoir |
| Confirmer | CircleCheck | Confirmer |
| Signaler | Flag* | Signaler |
| Alerte | Siren | Alerte |
| Vétérinaire | Stethoscope | Vétérinaire |
| Valider (vétérinaire) | ShieldCheck | Valider |
| Refuser | CircleX | Refuser |
| Carte | Map | Carte |
| Localiser | MapPin | Localiser |
| Historique | History | Historique |
| Santé | HeartPulse | Santé |
| Symptômes | Activity* | Symptômes |
| Photo | Camera | Photo |
| Rechercher | Search | Rechercher |
| Retour | ArrowLeft | Retour |
| Écouter (aide audio) | Volume2 | Écouter |
| Hors ligne | WifiOff | Hors ligne |
| En ligne | Wifi | En ligne |
| Envoyé | CloudCheck | Envoyé |
| En attente | Clock | En attente |
| À vérifier | TriangleAlert | À vérifier |
| Erreur | CircleAlert | Erreur |
| Information | Info | Information |
| Fermer | X | Fermer |
| Profil | UserRound | Profil |
| Quitter | LogOut | Quitter |

Les icônes marquées d'une étoile (*) sont à tester auprès de 5 personnes avant d'être figées. **Pictogrammes à ajouter** (absents de Lucide) : bovin, ovin, caprin, porc, volaille ; et les symptômes du signalement.

## 6. Vocabulaire et messages

Un seul mot par sens. Aucun synonyme sans accord de l'équipe. **Signaler** : quelqu'un rapporte une situation suspecte. **Confirmer** : quelqu'un confirme un transfert ou une réception. **Valider** : un vétérinaire prend une décision sanitaire.

| Mot officiel | À éviter |
|---|---|
| Accueil | Dashboard, tableau de bord (pour l'éleveur) |
| Animal | Sujet, spécimen |
| Élevage | Exploitation, centre, site (un seul mot dans les écrans) |
| Ajouter | Créer, enregistrer |
| Scanner | Lire, décoder |
| Transférer | Déplacer, muter |
| Recevoir | Réceptionner |
| Confirmer | Approuver, valider |
| Signaler | Notifier, alerter |
| Valider | Certifier, autoriser (réservé au vétérinaire) |
| Refuser | Rejeter |
| Envoyer | Synchroniser, transmettre |
| Rechercher | Filtrer, consulter |
| Écouter | Assistance audio |
| Historique | Journal, logs |
| À surveiller | Douteux |
| Contact possible | Contaminé, infecté, malade |
| Alerte validée | Confirmé malade |

### Messages types

| Situation | Message |
|---|---|
| Animal ajouté | Animal ajouté. |
| Scan réussi | Animal retrouvé. |
| Animal introuvable | Animal introuvable. Vérifiez l'étiquette. |
| Étiquette non reconnue | Étiquette non reconnue. Essayez encore ou saisissez le code. |
| Transfert | Transfert envoyé. |
| Réception | Réception enregistrée. |
| Confirmation | Transfert confirmé. |
| Signalement | Signalement envoyé au vétérinaire. |
| Contact possible (éleveur) | Un animal arrivé chez vous a peut-être été en contact avec un cas suspect. Appelez votre vétérinaire. |
| Alerte validée | Alerte validée par le vétérinaire. |
| Hors connexion | Pas de connexion. Vos données sont gardées sur ce téléphone. |
| En attente | Envoi en attente. |
| À vérifier | Ces informations ont changé. Vérifiez avant de continuer. |
| Champ manquant | Choisissez une réponse pour continuer. |

Règles : une phrase = une information ; deux phrases au plus pour une erreur ; présent et verbes concrets ; pas de code technique ; pas de double négation. Un message à un éleveur exposé ne révèle jamais l'élevage d'origine.

## 7. Navigation par profil

| Profil | Entrées |
|---|---|
| Éleveur, agent de terrain (mobile, 4 entrées) | Accueil, Animaux, Scanner (bouton central mis en valeur), Alertes. Les actions Ajouter, Transférer, Recevoir et Signaler sont de grands boutons de l'Accueil. |
| Vétérinaire (ordinateur, barre latérale) | Alertes, Signalements, Carte, Animaux |
| Administration (ordinateur, barre latérale) | Tableau de bord, Carte, Alertes, Règles (consultation) |

## 8. Composants

Chaque composant interactif prévoit ses états : normal, appuyé, désactivé, chargement, erreur. **Socle à construire en premier** (dans `components/ui` et `components/baobia`) :

| Composant | Rôle | Base |
|---|---|---|
| PrimaryButton, SecondaryButton, DangerButton | Action principale, secondaire, destructive | shadcn Button personnalisé |
| IconTextButton | Action avec icône et mot (grandes actions de l'Accueil) | Sur mesure |
| NumberStepper | Quantité par + et - | Sur mesure |
| ChoiceGrid | Choix visuel par grandes icônes (espèce, symptômes) | Sur mesure |
| TextInput | Saisie et recherche | shadcn Input personnalisé |
| HealthStatusBadge | 5 états sanitaires : couleur + icône + mot | Sur mesure |
| AlertLevelBadge | 3 niveaux d'alerte : signalement reçu, exposition potentielle, alerte validée | Sur mesure |
| SyncStatusBanner / OfflineBanner | Hors ligne, en attente, envoyé, à vérifier | Sur mesure |
| AppHeader | Marque, état du réseau, place de l'aide audio | Sur mesure |
| BottomNavigation | Navigation mobile, 4 entrées | Sur mesure |
| SidebarNavigation | Navigation ordinateur | Sur mesure |
| AnimalCard | Résumé d'un animal | Sur mesure |
| ConfirmDialog | Fenêtre de confirmation | shadcn Dialog personnalisé |
| Toast / Message | Retour de succès, d'erreur, d'information | shadcn Sonner / Alert personnalisés |
| EmptyState | Écran sans contenu | Sur mesure |
| LoadingState | Chargement | shadcn Skeleton |
| DemoDataNotice | Mention « illustration, données simulées » | Sur mesure |

**Ensuite, à la demande :** QRCodeFrame, AnimalProfile, AnimalTag, FarmCard, TransferCard, TransferConfirmation, HealthReportCard, Timeline, HealthLegend, ZoneStatusCard, MapZone, VeterinaryDecision, AlertList, AlertDetail, DashboardStatCard, DataTable, FilterBar, TimelineEvent, FarmMap. À construire à la demande, quand un écran en a besoin, en réutilisant le socle ci-dessus.

## 9. Gabarits d'écran

Toute nouvelle page réutilise un de ces gabarits.

**Liste** (exemples : Animaux, élevages, transferts, alertes)

- Mobile : En-tête + état du réseau ; titre ; recherche simple ; liste de cartes ; action principale ; navigation basse.
- Ordinateur : Barre latérale + en-tête ; titre ; recherche et filtres ; tableau ou grille ; action principale en haut.

**Formulaire en une action** (exemples : Ajout d'animal, signalement, choix d'élevage)

- Mobile : Progression ; une question claire ; choix visuels ou un champ ; bouton Continuer en bas ; aide audio réservée.
- Ordinateur : Question dans une colonne centrale ; choix en grille ; bouton sous le formulaire ; progression visible.

**Fiche détail** (exemples : Animal, élevage, transfert)

- Mobile : Retour ; identifiant très visible ; état sanitaire ; informations essentielles ; historique ; action principale en bas.
- Ordinateur : En-tête d'identification ; état sanitaire ; informations en colonnes ; historique ; actions visibles.

**Confirmation** (exemples : Réception, transfert, validation vétérinaire)

- Mobile : Question ; résumé de l'opération ; éléments importants ; bouton Confirmer ; bouton Retour.
- Ordinateur : Résumé en colonnes ; informations et historique ; bouton principal et action secondaire.

**Tableau de bord** (exemples : Accueil éleveur, vétérinaire, administration)

- Mobile : Un indicateur principal ; alertes prioritaires ; actions rapides ; navigation basse.
- Ordinateur : Indicateurs ; liste des alertes ; carte sanitaire ; tableaux et filtres ; navigation latérale.

Écrans de référence à dessiner en premier : Accueil éleveur, Scanner, Fiche animal, Signaler (choix des symptômes), Transférer, Confirmer une réception, Alerte vue par l'éleveur (message neutre), Alerte vue par le vétérinaire, Carte par zones.

## 10. Hors ligne : états à afficher

- État de connexion permanent, avec texte et icône.
- Distinguer une donnée gardée sur le téléphone d'une donnée reçue par le serveur.
- État de chaque opération : **En attente**, **Envoyé**, **À vérifier**.
- Ne jamais afficher « Envoyé » avant la confirmation du serveur.
- Message clair en cas de conflit ; une vérification humaine est demandée.
- Le comportement technique (PWA, stockage local, file d'envoi) est développé et testé séparément.

## 11. Carte et zones

Cinq états, chacun avec sa couleur, son contour sombre, son icône et son motif (tableau de la section 2). Une légende, un mot à côté de chaque couleur. Aucun nom d'élevage sur la carte. Une zone trop petite passe en « Pas assez de données ». Les couleurs sont illustratives dans la maquette 3D.

## 12. Fichier de thème (source de vérité)

À placer dans `src/styles/globals.css`. Vérifier la compatibilité avec la version de Tailwind et de shadcn réellement installées avant de copier.

```css
@import "tailwindcss";

:root {
  /* marque et neutres */
  --brand: #174A3B;  --brand-hover: #123D31;  --brand-light: #E8F0EC;
  --background: #F7F8F5;  --surface: #FFFFFF;  --surface-secondary: #EEF1ED;
  --foreground: #17231B;  --text-secondary: #59665D;
  --border: #D5DDD6;  --focus: #175CD3;

  /* 5 etats sanitaires : fond, texte, contour (ne pas modifier) */
  --health-normal: #287A45;    --health-normal-fg: #FFFFFF;  --health-normal-line: #1B5A33;
  --health-watch: #F7DC6F;     --health-watch-fg: #302500;   --health-watch-line: #8A6A00;
  --health-exposure: #E8740C;  --health-exposure-fg: #2B1600; --health-exposure-line: #9A4A05;
  --health-alert: #B42318;     --health-alert-fg: #FFFFFF;   --health-alert-line: #7F1A12;
  --health-unknown: #667085;   --health-unknown-fg: #FFFFFF; --health-unknown-line: #475467;

  /* fonctionnelles */
  --success: #176B3A;  --success-bg: #EAF5ED;
  --error: #9C2A56;    --error-bg: #FDEAF1;
  --info: #175CD3;     --info-bg: #EAF2FC;
  --warning: #8A4B08;  --warning-bg: #FFF4DF;

  --font-main: "Atkinson Hyperlegible", system-ui, sans-serif;
  --space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px;
  --space-5: 20px; --space-6: 24px; --space-8: 32px; --space-12: 48px;
  --touch-min: 48px; --touch-primary: 60px;
  --radius-sm: 8px; --radius-md: 12px; --radius-lg: 16px; --radius-xl: 20px;

  /* noms attendus par shadcn/ui (a verifier avec la version installee) */
  --card: var(--surface);  --card-foreground: var(--foreground);
  --popover: var(--surface);  --popover-foreground: var(--foreground);
  --primary: var(--brand);  --primary-foreground: #FFFFFF;
  --secondary: var(--surface-secondary);  --secondary-foreground: var(--foreground);
  --muted: var(--surface-secondary);  --muted-foreground: var(--text-secondary);
  --accent: var(--brand-light);  --accent-foreground: var(--brand);
  --destructive: var(--error);  --input: var(--border);  --ring: var(--focus);
  --radius: var(--radius-md);
}

@theme inline {
  --font-sans: var(--font-main);
  --color-background: var(--background);  --color-foreground: var(--foreground);
  --color-card: var(--card);  --color-card-foreground: var(--card-foreground);
  --color-popover: var(--popover);  --color-popover-foreground: var(--popover-foreground);
  --color-primary: var(--primary);  --color-primary-foreground: var(--primary-foreground);
  --color-secondary: var(--secondary);  --color-secondary-foreground: var(--secondary-foreground);
  --color-muted: var(--muted);  --color-muted-foreground: var(--muted-foreground);
  --color-accent: var(--accent);  --color-accent-foreground: var(--accent-foreground);
  --color-destructive: var(--destructive);
  --color-border: var(--border);  --color-input: var(--input);  --color-ring: var(--ring);
  /* etats sanitaires : classes bg-health-alert, text-health-alert-fg, border-health-alert-line... */
  --color-health-normal: var(--health-normal);
  --color-health-normal-fg: var(--health-normal-fg);
  --color-health-normal-line: var(--health-normal-line);
  --color-health-watch: var(--health-watch);
  --color-health-watch-fg: var(--health-watch-fg);
  --color-health-watch-line: var(--health-watch-line);
  --color-health-exposure: var(--health-exposure);
  --color-health-exposure-fg: var(--health-exposure-fg);
  --color-health-exposure-line: var(--health-exposure-line);
  --color-health-alert: var(--health-alert);
  --color-health-alert-fg: var(--health-alert-fg);
  --color-health-alert-line: var(--health-alert-line);
  --color-health-unknown: var(--health-unknown);
  --color-health-unknown-fg: var(--health-unknown-fg);
  --color-health-unknown-line: var(--health-unknown-line);
  --color-success: var(--success);  --color-success-bg: var(--success-bg);
  --color-error: var(--error);  --color-error-bg: var(--error-bg);
  --color-info: var(--info);  --color-info-bg: var(--info-bg);
  --color-warning: var(--warning);  --color-warning-bg: var(--warning-bg);
  --radius-sm: var(--radius-sm); --radius-md: var(--radius-md); --radius-lg: var(--radius-lg); --radius-xl: var(--radius-xl);
}
```

## 13. Tests de simplicité

Avant de valider un écran, le faire essayer à une personne sans explication.

1. L'action principale est-elle trouvée en moins de 3 secondes ?
2. Le sens de l'action est-il compris sans explication ?
3. Chaque action a-t-elle une icône et un mot court ?
4. L'écran est-il utilisable avec un doigt, sans précision excessive ?
5. Les textes restent-ils lisibles en forte luminosité ?
6. L'utilisateur distingue-t-il les données en attente, envoyées et à vérifier ?
7. Le message d'erreur indique-t-il une action corrective simple ?
8. L'état reste-t-il compréhensible sans percevoir la couleur ?

Scénarios : « Ajoute une chèvre. » « Retrouve cet animal avec son étiquette. » « Déclare le départ de ces animaux. » « Confirme que tu as reçu les animaux. » « Signale que cet animal semble malade. »

## 14. Règles de développement

- Pas de couleur hexadécimale ni de dimension écrite à la main dans un composant : utiliser les variables.
- Pas de nouveau mot sans accord de l'équipe.
- Chaque composant métier documente ses états et son comportement hors ligne.
- Toute demande de fusion qui touche l'interface est relue par le chef de projet.
- La maquette 3D reprend les mêmes couleurs, rayons et proportions.

## 15. Décisions à confirmer

| Sujet | Décision ou question |
|---|---|
| Mot « Élevage » partout | Remplace « centre » dans les écrans ; « center » reste le nom technique dans le code. |
| Libellé « Contact possible » | Pour l'état « exposition potentielle ». À valider avec un vétérinaire (ton non stigmatisant). |
| Couleur d'erreur distincte du rouge d'alerte | Rouge réservé à l'alerte validée ; erreurs en rose-prune (#9C2A56) avec forme de message différente. |
| Entrées de navigation par profil | Proposition de la section 7, à confirmer avec les cas d'usage. |
| Pictogrammes à dessiner | Espèces (bovin, ovin, caprin, porc, volaille) et symptômes : absents de Lucide. Jeu libre ou SVG dessinés, licence vérifiée. |
| Liste des symptômes | À fixer avec un vétérinaire ; 6 à 8 maximum pour le prototype. |
| Compréhension des icônes | Tester avec 5 personnes les icônes marquées d'une étoile dans la section 5 avant de les figer. |
| Marque et vert Normal | Deux verts proches (ratio 1,9:1) : à regarder sur un vrai téléphone. Sinon assombrir la marque. |

---

*BAOBIA, une interface simple pour identifier, tracer, surveiller et alerter.*
