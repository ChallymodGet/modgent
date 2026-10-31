/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Surface Tokens - Monochrome Base
        surface: {
          primary: {
            light: '#FFFFFF',
            dark: '#0A0A0A',
          },
          secondary: {
            light: '#F5F5F7',
            dark: '#171717',
          },
          tertiary: {
            light: '#E5E5EA',
            dark: '#262626',
          },
        },
        // Accent Tokens - High Contrast
        accent: {
          primary: '#4F46E5', // Deep Indigo
          primaryHover: '#4338CA',
          ai: '#8B5CF6', // Intelligence Purple
        },
        // Semantic Tokens
        semantic: {
          success: '#10B981',
          warning: '#F59E0B',
          error: '#EF4444',
          info: '#3B82F6',
        },
      },
      fontFamily: {
        sans: ['Inter', 'Geist', 'ui-sans-serif', 'system-ui'],
        mono: ['JetBrains Mono', 'Roboto Mono', 'ui-monospace', 'SFMono-Regular'],
      },
      spacing: {
        // Strict 8px Base Unit System
        'safe': '8px',
        'xs': '8px',
        'sm': '16px',
        'md': '24px',
        'lg': '32px',
        'xl': '48px',
        '2xl': '64px',
      },
      borderRadius: {
        'none': '0',
        'xs': '2px',
        'sm': '4px',
        'md': '8px',
        'lg': '12px',
        'xl': '16px',
        'full': '9999px',
      },
      boxShadow: {
        'glass': '0 4px 30px rgba(0, 0, 0, 0.1)',
        'soft': '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
      }
    },
  },
  plugins: [],
}
