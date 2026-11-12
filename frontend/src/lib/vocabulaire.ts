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
  signalements: 'Signalements', // charte, section 7 (navigation vétérinaire)
  // À VALIDER : absents de la charte.
  seConnecter: 'Se connecter',
  mouvements: 'Mouvements',
  afficher: 'Afficher',
  cacher: 'Cacher',
  plus: 'Plus',
  moins: 'Moins',
} as const

/** Les 5 états sanitaires (carte, badges, maquette 3D). */
export const etatsSanitaires = {
  normal: 'Normal',
  watch: 'À surveiller',
  exposure: 'Contact possible',
  alert: 'Alerte validée',
  unknown: 'Pas assez de données',
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
} as const

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
} as const

/** Libellés des champs et aides. */
export const champs = {
  telephone: 'Numéro de téléphone',
  telephoneAide: 'Exemple : 07 07 07 07 07',
  motDePasse: 'Mot de passe',
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
  quelleEtiquette: 'Quelle étiquette ?',
} as const
