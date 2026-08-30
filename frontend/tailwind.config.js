module.exports = {
  presets: [
    require('frappe-ui/src/utils/tailwind.config')
  ],
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
    "./node_modules/frappe-ui/src/components/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Deep Navy — primary brand
        // Source: old globals.css --deep-navy: 214 98% 16% = #012350
        navy: {
          50: '#f0f4fa',
          100: '#d9e2f1',
          200: '#b3c5e3',
          300: '#7d9fce',
          400: '#486fb0',
          500: '#2c4f8f',
          600: '#1955a0',  // primary-soft (214 70% 30%)
          700: '#0c2e6e',  // deep-navy-hover (214 80% 24%)
          800: '#012350',  // deep-navy (214 98% 16%) — MAIN
          900: '#001224',
          950: '#000912',
        },
        // Muted Gold — accent
        // Source: old globals.css --accent: 38 46% 48% = #b38942
        gold: {
          50: '#fdfbf3',
          100: '#faf3dc',
          200: '#f4e6b3',
          300: '#e6d3a8',  // accent-soft-border (38 50% 82%)
          400: '#c89a55',
          500: '#b38942',  // accent (38 46% 48%) — MAIN
          600: '#9d6d2e',  // accent-hover (37 50% 41%)
          700: '#7a5524',
          800: '#5c401c',
          900: '#3d2a13',
        },
        // Warm Ivory — background
        // Source: old globals.css --background: 43 12% 97% = #f7f6f3
        ivory: {
          50: '#fefdfb',
          100: '#fbfaf7',
          200: '#f7f6f3',  // background (43 12% 97%) — MAIN
          300: '#e8e4d9',  // border (40 16% 88%)
        },
      },
      fontFamily: {
        sans: ['Cairo', 'Tajawal', 'system-ui', 'sans-serif'],
        display: ['Cairo', 'Tajawal', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        'xl': '14px',
        '2xl': '18px',
        '3xl': '24px',
      },
      boxShadow: {
        'soft': '0 1px 3px 0 rgba(0, 0, 0, 0.03), 0 1px 2px -1px rgba(0, 0, 0, 0.03)',
        'soft-md': '0 4px 6px -1px rgba(0, 0, 0, 0.04), 0 2px 4px -2px rgba(0, 0, 0, 0.03)',
        'soft-lg': '0 10px 15px -3px rgba(0, 0, 0, 0.04), 0 4px 6px -4px rgba(0, 0, 0, 0.03)',
        'glow-gold': '0 0 0 3px rgba(179, 137, 66, 0.15)',
        'glow-navy': '0 0 0 3px rgba(1, 35, 80, 0.12)',
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'scale-in': 'scaleIn 0.15s ease-out',
      },
      keyframes: {
        fadeIn: { '0%': { opacity: 0 }, '100%': { opacity: 1 } },
        slideUp: { '0%': { opacity: 0, transform: 'translateY(8px)' }, '100%': { opacity: 1, transform: 'translateY(0)' } },
        scaleIn: { '0%': { opacity: 0, transform: 'scale(0.96)' }, '100%': { opacity: 1, transform: 'scale(1)' } },
      },
    },
  },
  plugins: [],
}
