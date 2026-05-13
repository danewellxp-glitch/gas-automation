/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'sans-serif'],
      },
      colors: {
        primary: {
          50:  '#fff7ed',
          100: '#ffedd5',
          200: '#fed7aa',
          300: '#fdba74',
          400: '#fb923c',
          500: '#f97316',
          600: '#ea580c',
          700: '#c2410c',
          800: '#9a3412',
          900: '#7c2d12',
          950: '#431407',
        },
      },
      boxShadow: {
        'xs': '0 1px 2px 0 rgb(0 0 0 / 0.05)',
      },
      keyframes: {
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'fade-in-up': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-in-right': {
          '0%': { opacity: '0', transform: 'translateX(16px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        'scale-in': {
          '0%': { opacity: '0', transform: 'scale(0.96)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        'highlight-fade': {
          '0%': { backgroundColor: 'rgba(16, 185, 129, 0.18)', transform: 'translateY(-4px)' },
          '100%': { backgroundColor: 'transparent', transform: 'translateY(0)' },
        },
        'pulse-slow': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' },
        },
        'draw-line': {
          '0%': { strokeDashoffset: '200' },
          '100%': { strokeDashoffset: '0' },
        },
      },
      animation: {
        'fade-in':         'fade-in 200ms ease-out',
        'fade-in-up':      'fade-in-up 300ms cubic-bezier(0.4, 0, 0.2, 1) both',
        'slide-in-right':  'slide-in-right 250ms cubic-bezier(0.4, 0, 0.2, 1) both',
        'scale-in':        'scale-in 200ms cubic-bezier(0.4, 0, 0.2, 1) both',
        'highlight-fade':  'highlight-fade 1800ms ease-out both',
        'pulse-slow':      'pulse-slow 2s ease-in-out infinite',
        'draw-line':       'draw-line 1200ms ease-out both',
      },
      transitionTimingFunction: {
        'standard': 'cubic-bezier(0.4, 0, 0.2, 1)',
      },
    },
  },
  plugins: [],
}
