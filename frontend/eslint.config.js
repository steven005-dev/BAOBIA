import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

// Règles de la charte (docs/BAOBIA_UI_GUIDELINES.md, section 14), vérifiées sur chaque texte du code.
const CHARTER_CHECKS = [
  [/#[0-9A-Fa-f]{3,8}|rgba?\(|hsla?\(/, 'Couleur écrite à la main : utilisez une variable du thème (globals.css).'],
  [/\[\d+(\.\d+)?(px|rem|em)\]/, 'Taille écrite à la main : utilisez une variable du thème (globals.css).'],
  [/contamin|infect/i, 'Mot interdit : un élevage est « exposé » (« Contact possible »), jamais « contaminé ».'],
]
const charterPlugin = {
  rules: {
    'theme-and-words': {
      meta: { type: 'problem', schema: [] },
      create(context) {
        const check = (node, text) => {
          for (const [pattern, message] of CHARTER_CHECKS) {
            if (pattern.test(text)) context.report({ node, message })
          }
        }
        return {
          Literal: (node) => typeof node.value === 'string' && check(node, node.value),
          TemplateElement: (node) => check(node, node.value.raw),
          JSXText: (node) => check(node, node.value),
        }
      },
    },
  },
}
const charterRules = { 'baobia/theme-and-words': 'error' }

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
    },
    plugins: { baobia: charterPlugin },
    rules: charterRules,
  },
  {
    // Fichiers qui exportent des fournisseurs et leurs hooks ensemble.
    files: ['src/auth/**', 'src/components/Toast.tsx', 'src/components/fieldContext.ts', 'src/offline/**', 'src/features/**/routes.tsx', 'src/app/router.tsx'],
    rules: { 'react-refresh/only-export-components': 'off' },
  },
])
