/**
 * Vocabulaire officiel de l'interface BAOBIA (docs/BAOBIA_UI_GUIDELINES.md, section 6).
 *
 * TOUS les textes affichés viennent d'ici : un seul mot par sens, dans toute l'application.
 * - « Signaler » : quelqu'un rapporte une situation suspecte.
 * - « Confirmer » : quelqu'un confirme un transfert ou une réception.
 * - « Valider » : un vétérinaire prend une décision sanitaire (réservé au vétérinaire).
 * Un élevage exposé est « Contact possible », jamais « contaminé » (interdit par le lint).
 * Ajouter un mot = accord de l'équipe d'abord. Les mots marqués « À VALIDER » ne sont pas
 * encore dans la charte.
 *
 * Exemple : import { mots, messages } from '@/lib/vocabulaire'
 *           <Button icon={CircleCheck}>{mots.confirmer}</Button>
 */

export const APP_NAME = 'BAOBIA'

/** Mots d'action et de navigation (un mot = une action). */
export const mots = {
  accueil: 'Accueil',
  animal: 'Animal',
  animaux: 'Animaux',
  lot: 'Lot',
  elevage: 'Élevage',
  elevages: 'Élevages',
  etiquette: 'Étiquette',
  scanner: 'Scanner',
  ajouter: 'Ajouter',
  modifier: 'Modifier',
  supprimer: 'Supprimer',
  transferer: 'Transférer',
  recevoir: 'Recevoir',
  confirmer: 'Confirmer',
  signaler: 'Signaler',
  alerte: 'Alerte',
  alertes: 'Alertes',
  veterinaire: 'Vétérinaire',
  valider: 'Valider',
  refuser: 'Refuser',
  carte: 'Carte',
  localiser: 'Localiser',
  historique: 'Historique',
  sante: 'Santé',
  symptomes: 'Symptômes',
  photo: 'Photo',
  rechercher: 'Rechercher',
  retour: 'Retour',
  ecouter: 'Écouter',
  envoyer: 'Envoyer',
  horsLigne: 'Hors ligne',
  enLigne: 'En ligne',
  envoye: 'Envoyé',
  enAttente: 'En attente',
  aVerifier: 'À vérifier',
  erreur: 'Erreur',
  information: 'Information',
  fermer: 'Fermer',
  profil: 'Profil',
  quitter: 'Quitter',
  continuer: 'Continuer',
  etiquettes: 'Étiquettes', // À VALIDER (pluriel d'« Étiquette »)
  imprimer: 'Imprimer', // À VALIDER : imprimer l'étiquette d'un animal
  signalements: 'Signalements', // charte, section 7 (navigation vétérinaire)
  // À VALIDER : absents de la charte.
  seConnecter: 'Se connecter',
  mouvements: 'Mouvements',
  afficher: 'Afficher',
  cacher: 'Cacher',
  plus: 'Plus',
  moins: 'Moins',
  inscrire: 'Inscrire', // À VALIDER : l'agent inscrit un éleveur
} as const

/** Les 5 états sanitaires (carte, badges, maquette 3D). */
export const etatsSanitaires = {
  normal: 'Normal',
  watch: 'À surveiller',
  exposure: 'Contact possible',
  alert: 'Alerte validée',
  unknown: 'Pas assez de données',
} as const

/** Noms des profils, affichés dans la marque de l'espace (en-tête, barre latérale).
 *  À VALIDER : absents de la charte. */
export const profils = {
  breeder: 'Éleveur',
  field_agent: 'Agent de terrain',
  trader: 'Commerçant',
  veterinarian: 'Vétérinaire',
  authority: 'Autorité',
} as const

/** Les 3 niveaux d'alerte (charte, section 8 : AlertLevelBadge). */
export const niveauxAlerte = {
  1: 'Signalement reçu',
  2: 'Exposition potentielle',
  3: 'Alerte validée',
} as const

/** États d'envoi d'une opération (charte, section 10). */
export const etatsEnvoi = {
  pending: 'En attente',
  sent: 'Envoyé',
  check: 'À vérifier',
} as const

/** Messages types (charte, section 6). Une phrase = une information. */
export const messages = {
  animalAjoute: 'Animal ajouté.',
  scanReussi: 'Animal retrouvé.',
  animalIntrouvable: "Animal introuvable. Vérifiez l'étiquette.",
  etiquetteNonReconnue: 'Étiquette non reconnue. Essayez encore ou saisissez le code.',
  transfertEnvoye: 'Transfert envoyé.',
  receptionEnregistree: 'Réception enregistrée.',
  transfertConfirme: 'Transfert confirmé.',
  signalementEnvoye: 'Signalement envoyé au vétérinaire.',
  contactPossibleEleveur:
    'Un animal arrivé chez vous a peut-être été en contact avec un cas suspect. Appelez votre vétérinaire.',
  alerteValidee: 'Alerte validée par le vétérinaire.',
  horsConnexion: 'Pas de connexion. Vos données sont gardées sur ce téléphone.',
  enAttente: 'Envoi en attente.',
  aVerifier: 'Ces informations ont changé. Vérifiez avant de continuer.',
  champManquant: 'Choisissez une réponse pour continuer.',
  // À VALIDER : messages du socle, absents de la charte.
  donneesSimulees: 'Illustration : données simulées.',
  chargement: 'Chargement…',
  pageVide: 'Cet écran arrive bientôt.',
  pageIntrouvable: "Cette page n'existe pas.",
  // À VALIDER : messages du module identity (élevages, animaux, scan).
  lotAjoute: 'Lot ajouté.',
  aucunElevage: 'Aucun élevage',
  aucunElevageAide: 'Demandez à votre agent de terrain de créer votre élevage.',
  aucunAnimal: 'Aucun animal',
  aucunAnimalAide: 'Ajoutez votre premier animal avec son étiquette.',
  etiquetteNonPosee: "Cette étiquette n'est posée sur aucun animal.",
  etiquetteRemplacee: "Étiquette remplacée. Voici l'animal qui la portait.",
  etiquettePerdue: 'Étiquette déclarée perdue.',
  pasDansVosElevages: "Cet animal n'est pas dans vos élevages.",
  visezEtiquette: "Visez le QR code de l'étiquette.",
  cameraIndisponible: 'Caméra indisponible. Saisissez le code.',
  // À VALIDER : messages reçus (Accueil).
  nouveauxMessages: 'Nouveaux messages',
  etiquetteChangee: 'Étiquette changée.',
  gardeSurTelephone: "Pas de réponse du réseau : c'est gardé sur ce téléphone et partira tout seul.",
  etiquetteDejaImprimable: "Vous pouvez déjà imprimer l'étiquette.",
  codePourEtiquette: "Imprimez cette étiquette et posez-la sur l'animal.",
  elevageAjoute: 'Élevage ajouté.',
  etiquettesRemises: 'Étiquettes remises.',
  aucuneEtiquette: 'Aucune étiquette ajoutée.',
  etiquetteDejaDansLaListe: 'Cette étiquette est déjà dans la liste.',
  // À VALIDER : inscription d'un éleveur par l'agent de terrain.
  eleveurInscrit: 'Éleveur inscrit.',
  remettreIdentifiants: "Donnez ce numéro et ce mot de passe à l'éleveur. Il s'en sert pour se connecter.",
  // À VALIDER : notice lue à l'éleveur (loi 2013-450). Changer ce texte = changer
  // CONSENT_NOTICE_VERSION dans backend/apps/identity/serializers.py.
  noticeDonnees:
    "BAOBIA garde votre nom, votre numéro et vos animaux pour suivre les maladies. Seuls les vétérinaires et les services de l'État de votre zone les voient. Les autres éleveurs ne voient jamais le nom de votre élevage. Vous pouvez demander à votre agent de voir ou de corriger vos informations.",
  accordObligatoire: "L'accord de l'éleveur est obligatoire.",
  inscriptionEnAttente: "L'inscription partira toute seule au retour du réseau. Vous pouvez déjà donner le mot de passe.",
  // À VALIDER : boucle préimprimée (spec v1.4).
  boucleLue: 'Boucle lue.',
  motDePasseChange: 'Mot de passe changé.', // À VALIDER
  aucunSignalement: 'Aucun signalement pour cet animal.', // À VALIDER
  scannezLaBoucle: 'Scannez la boucle ou saisissez son code.',
} as const

/**
 * Textes des messages envoyés par le serveur (backend : notifications/services.py, MESSAGES).
 * Le serveur n'envoie qu'un code : le texte est choisi ici. Jamais l'élevage d'origine.
 */
export const textesNotifications: Record<string, string> = {
  'exposure.contact_possible': messages.contactPossibleEleveur,
  'alert.validated': messages.alerteValidee,
  // À VALIDER : messages aux vétérinaires et à l'autorité (alerte de zone).
  'zone_cluster.review_requested': 'Plusieurs signalements dans votre zone. Votre avis est demandé.',
  'zone_cluster.escalated': 'Rappel : des signalements attendent toujours un avis.',
  'alert.review_disagreement': "Deux vétérinaires ne sont pas d'accord sur une alerte.",
}

/** Messages d'erreur du client API et de la connexion (À VALIDER, ton de la charte). */
export const erreurs = {
  reseau: 'Pas de connexion. Réessayez quand le réseau revient.',
  lent: 'Le réseau est trop lent. Réessayez.',
  serveur: 'Le service ne répond pas. Réessayez plus tard.',
  sessionExpiree: 'Session expirée. Connectez-vous à nouveau.',
  interdit: "Vous n'avez pas accès à cette action.",
  introuvable: 'Information introuvable.',
  saisie: 'Vérifiez les informations saisies.',
  tropDEssais: "Trop d'essais. Attendez une minute.",
  connexion: 'Numéro ou mot de passe incorrect.',
  telephoneIncomplet: 'Le numéro doit avoir 10 chiffres.',
  codeIncomplet: 'Le code doit avoir 9 caractères.',
  codeIncorrect: "Code incorrect. Vérifiez l'étiquette.",
  motDePasseVide: 'Écrivez votre mot de passe.',
  motDePasseCourt: 'Au moins 8 caractères.', // À VALIDER
} as const

/** Libellés des champs et aides. */
export const champs = {
  telephone: 'Numéro de téléphone',
  telephoneAide: 'Exemple : 07 07 07 07 07',
  motDePasse: 'Mot de passe',
  // À VALIDER : changer son mot de passe.
  motDePasseActuel: 'Mot de passe actuel',
  nouveauMotDePasse: 'Nouveau mot de passe',
  nouveauMotDePasseAide: 'Au moins 8 caractères, pas trop simple.',
  codeEtiquette: "Code de l'étiquette",
  codeEtiquetteAide: '9 caractères, écrits sous le QR code',
  espece: 'Espèce',
  choisir: 'Choisir…',
  quantite: 'Nombre',
  // À VALIDER : champs du module identity.
  nom: 'Nom',
  ajouteLe: 'Ajouté le',
  etape: 'Étape',
  sur: 'sur',
  etiquettePerdue: 'Perdue',
  etiquetteAbimee: 'Abîmée',
  mauvaiseEtiquette: 'Mauvaise étiquette',
  nomElevage: "Nom de l'élevage",
  zone: 'Zone',
  especesElevees: 'Espèces élevées',
  nomEleveur: "Nom de l'éleveur",
  accordEleveur: "L'éleveur a écouté et il est d'accord", // À VALIDER
  lireEleveur: "À lire à l'éleveur", // À VALIDER
  // À VALIDER : boucle préimprimée (spec v1.4).
  scannerBoucle: 'Scanner la boucle',
  creerCode: 'Pas de boucle : créer un code',
} as const

/** Titres d'écran. */
export const titres = {
  connexion: 'Connexion',
  composants: 'Composants (développement)',
  // À VALIDER : titres du module identity.
  ajouterAnimal: 'Ajouter un animal',
  quelleEspece: 'Quelle espèce ?',
  animalOuLot: 'Un animal ou un lot ?',
  combienAnimaux: "Combien d'animaux dans le lot ?",
  changerEtiquette: "Changer l'étiquette",
  pourquoiChanger: "Pourquoi changer l'étiquette ?",
  ajouterElevage: 'Ajouter un élevage',
  remettreEtiquettes: 'Remettre des étiquettes',
  inscrireEleveur: 'Inscrire un éleveur',
  ajouterSesAnimaux: 'Ajouter ses animaux',
  quelleEtiquette: 'Quelle étiquette ?', // À VALIDER
  changerMotDePasse: 'Changer mon mot de passe', // À VALIDER
} as const

/**
 * À VALIDER : module santé, alertes et carte (Yéo). Mots simples, sans nom de maladie
 * pour l'éleveur ; « Contact possible », jamais « contaminé ».
 */
export const sante = {
  titreSignaler: 'Signaler un cas',
  quelElevage: 'Quel élevage ?',
  queSePasseTIl: 'Que se passe-t-il ?',
  quelsSignes: 'Quels signes voyez-vous ?',
  quelsSignesAide: 'Touchez tous les signes que vous voyez. Vous pouvez passer.',
  quelsAnimaux: 'Quels animaux ?',
  quelsAnimauxAide: 'Touchez les animaux malades. Vous pouvez passer.',
  combienTouches: "Combien d'animaux sont touchés ?",
  // À VALIDER (spec v1.4, Y1) : morts et malades comptés à part.
  combienMorts: 'Combien de morts ?',
  combienMortsAide: "Mettez 0 si aucun animal n'est mort.",
  combienMalades: 'Combien de malades ?',
  combienMaladesAide: 'Animaux vivants qui ont des signes.',
  morts: 'Morts',
  malades: 'Malades',
  mesSignalements: 'Mes signalements',
  aExaminer: 'À examiner',
  aucunSignalement: 'Aucun signalement',
  aucunSignalementAide: 'Si un animal semble malade, touchez Signaler.',
  signaleLe: 'Signalé le',
  animauxTouches: 'Animaux touchés',
  decisionVeterinaire: 'Décision du vétérinaire',
  maladieRetenue: 'Maladie retenue',
  motif: 'Motif',
  motifAide: 'Obligatoire pour refuser.',
  decisionEnregistree: 'Décision enregistrée.',
  aucuneRegle: 'Aucune règle sanitaire pour cette maladie.',
} as const

export const typesSignalement = {
  suspicion: 'Animal malade',
  death: 'Animal mort',
  abnormal_mortality: 'Plusieurs morts',
} as const

export const etatsSignalement = {
  submitted: 'Reçu',
  under_review: 'En examen',
  validated: 'Validé',
  rejected: 'Refusé',
  closed: 'Clôturé',
} as const

export const decisionsVeterinaire = {
  request_info: 'Demander des informations',
  retain_suspicion: 'Garder la suspicion',
  raise_level2: 'Passer au niveau 2',
  validate_level3: 'Valider (niveau 3)',
  dismiss: 'Refuser',
  close: 'Clôturer',
} as const

export const alertesTextes = {
  aucuneAlerte: 'Aucune alerte',
  aucuneAlerteAide: 'Les alertes de votre zone apparaîtront ici.',
  mesMessages: 'Mes messages',
  aucunMessage: 'Aucun message',
  elevagesContact: 'Élevages en contact possible',
  elevagesEcartes: 'Élevages écartés',
  ecarte: 'Écarté',
  aucunContact: 'Aucun élevage en contact possible.',
  chemin: 'Chemin',
  foyer: 'Élevage signalé',
  regle: 'Règle appliquée',
  regleExperimentale: 'Valeurs de démonstration, à valider par un vétérinaire.',
  jours: 'jours',
  profondeur: 'Profondeur',
  confianceReduite: "Confiance réduite : un mouvement est contesté ou déclaré d'un seul côté.",
  // À VALIDER (spec v1.4, 9.6) : statut d'un mouvement du chemin, vu par le vétérinaire.
  unSeulCote: "Transfert déclaré d'un seul côté",
  conteste: 'Transfert contesté',
  ouverteLe: 'Ouverte le',
  valideePar: 'Validée par',
  pasUnDiagnostic: 'Contact possible ne veut pas dire malade.',
} as const

export const raisonsExposition: Record<string, string> = {
  sent_from_focus: "Animaux partis de l'élevage signalé",
  sent_after_exposure: 'Animaux partis après le contact',
  outside_window: 'Hors de la période à risque',
  unconfirmed_not_counted: 'Transfert pas encore confirmé',
  movement_cancelled: 'Transfert annulé',
  movement_expired: 'Transfert expiré',
}

export const carteTextes = {
  titre: 'Carte par zones',
  legende: 'Légende',
  toutesEspeces: 'Toutes',
  elevagesDansZone: 'élevages',
  animauxDansZone: 'animaux',
  mesElevages: 'Mes élevages',
  aucuneZone: 'Aucune zone à afficher',
  majLe: 'Mis à jour le',
  pasDeNom: "Aucun nom d'élevage n'est affiché.",
  // À VALIDER : carte de Côte d'Ivoire (districts, régions, points des élevages).
  titreCi: "Carte sanitaire de Côte d'Ivoire",
  districts: 'Districts',
  regions: 'Régions',
  voirRegions: 'Voir ses régions',
  retourPays: 'Tout le pays',
  touchezZone: 'Touchez une zone pour voir son état.',
  pointElevage: 'Un élevage',
  pointMarche: 'Un marché',
  pointGroupe: "Plusieurs élevages (le nombre est écrit dans le rond)",
  pointsReserves: 'Les points des élevages sont visibles par le vétérinaire et l’Autorité seulement.',
  aucunElevage: 'Aucun élevage enregistré dans cette zone.',
  listeZones: 'Liste des zones',
  sourceTraces: 'Limites : geoBoundaries (CC BY 4.0).',
} as const
