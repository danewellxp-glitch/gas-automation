/**
 * ESLint config — Cycle 1 baseline.
 *
 * Goal: catch correctness issues (undefined vars, broken hooks, parse errors)
 * without blocking CI on cosmetic noise across the existing ~87-component
 * codebase. Style rules will be ratcheted up in later cycles.
 *
 * Roadmap reference: docs/relatorios/ARCHITECTURE_HEALTH_REPORT_2026-04-30.md §4 Cycle 1.
 */
module.exports = {
  root: true,
  env: {
    browser: true,
    es2022: true,
    node: true,
  },
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    ecmaFeatures: { jsx: true },
  },
  settings: {
    react: { version: '18' },
  },
  extends: [
    'eslint:recommended',
    'plugin:react/recommended',
    'plugin:react/jsx-runtime',
    'plugin:react-hooks/recommended',
  ],
  plugins: ['react-refresh'],
  ignorePatterns: [
    'dist',
    'dist-build',
    'build',
    'coverage',
    'node_modules',
    'android',
    'public',
    '*.config.js',
    '*.config.cjs',
    'postcss.config.*',
    'tailwind.config.*',
    'vite.config.*',
    'vitest.config.*',
  ],
  rules: {
    // Correctness — fail the build.
    'no-undef': 'error',
    'no-unreachable': 'error',
    'no-dupe-keys': 'error',
    'no-dupe-args': 'error',
    'no-cond-assign': 'error',
    'react-hooks/rules-of-hooks': 'error',

    // Hot-reload safety — warn only, ratchet later.
    'react-refresh/only-export-components': 'off',

    // Noise we explicitly tolerate during Cycle 1.
    'no-unused-vars': [
      'warn',
      {
        argsIgnorePattern: '^_',
        varsIgnorePattern: '^_',
        ignoreRestSiblings: true,
      },
    ],
    'no-empty': ['warn', { allowEmptyCatch: true }],
    'no-prototype-builtins': 'warn',
    'no-useless-escape': 'warn',
    'no-constant-condition': ['warn', { checkLoops: false }],
    'no-irregular-whitespace': 'warn',
    'no-async-promise-executor': 'warn',

    'react/prop-types': 'off',
    'react/no-unknown-property': 'warn',
    'react/no-unescaped-entities': 'off',
    'react/display-name': 'off',
    'react/jsx-no-target-blank': 'warn',
    'react-hooks/exhaustive-deps': 'warn',
  },
  overrides: [
    {
      files: ['**/__tests__/**', '**/*.test.{js,jsx,ts,tsx}', 'src/test/**'],
      env: { jest: true, node: true },
      globals: {
        vi: 'readonly',
        describe: 'readonly',
        it: 'readonly',
        test: 'readonly',
        expect: 'readonly',
        beforeAll: 'readonly',
        beforeEach: 'readonly',
        afterAll: 'readonly',
        afterEach: 'readonly',
      },
    },
  ],
};
