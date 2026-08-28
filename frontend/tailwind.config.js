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
        navy: {
          50: '#f0f4fa',
          100: '#d9e2f1',
          200: '#b3c5e3',
          300: '#7d9fce',
          400: '#486fb0',
          500: '#2c4f8f',
          600: '#1e3a72',
          700: '#162c5a',
          800: '#0f1f42',
          900: '#0a1530',
          950: '#060d1f',
        },
        // Muted Gold — accent
        gold: {
          50: '#fdfbf3',
          100: '#faf3dc',
          200: '#f4e6b3',
          300: '#ecd07f',
          400: '#e3b94b',
          500: '#d4a02c',
          600: '#b87f22',
          700: '#92611e',
          800: '#6e481c',
          900: '#4a3115',
        },
        // Warm Ivory — background
        ivory: {
          50: '#fefdfb',
          100: '#faf8f3',
          200: '#f5f1e8',
          300: '#ede7d6',
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
        'soft': '0 1px 3px 0 rgba(15, 31, 66, 0.06), 0 1px 2px 0 rgba(15, 31, 66, 0.04)',
        'soft-md': '0 4px 12px -2px rgba(15, 31, 66, 0.08), 0 2px 6px -2px rgba(15, 31, 66, 0.05)',
        'soft-lg': '0 12px 32px -8px rgba(15, 31, 66, 0.12), 0 4px 12px -4px rgba(15, 31, 66, 0.06)',
        'glow-gold': '0 0 0 3px rgba(212, 160, 44, 0.15)',
        'glow-navy': '0 0 0 3px rgba(30, 58, 114, 0.12)',
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
