import js from '@eslint/js';
import globals from 'globals';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import tseslint from 'typescript-eslint';
import { defineConfig, globalIgnores } from 'eslint/config';
import prettier from 'eslint-config-prettier';

export default defineConfig([
  globalIgnores(['dist', 'node_modules']),

  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      ...tseslint.configs.recommended,

      // React (light, not annoying)
      react.configs.flat.recommended,

      // Hooks rules (important)
      reactHooks.configs.flat.recommended,

      // Vite refresh rules
      reactRefresh.configs.vite,

      // Must be last: turns off rules that conflict with Prettier
      prettier,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    settings: {
      react: { version: 'detect' },
    },
    rules: {
      // React 17+ / Vite: no need to import React
      'react/react-in-jsx-scope': 'off',

      // During scaffolding: warn, don’t block
      '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/no-explicit-any': 'warn',

      // Too strict during early setup; enable later if you want
      'react-hooks/set-state-in-effect': 'off',

      // optional: allow console while building
      'no-console': 'off',
    },
  },
]);
