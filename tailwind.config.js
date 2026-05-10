/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        black: '#000000',
        'liquid-white': 'rgba(255, 255, 255, 0.05)',
        'liquid-white-hover': 'rgba(255, 255, 255, 0.08)',
        'liquid-border': 'rgba(255, 255, 255, 0.10)',
        'liquid-border-hover': 'rgba(255, 255, 255, 0.20)',
        'bubble-white': 'rgba(255, 255, 255, 0.15)',
        'bubble-green': 'rgba(34, 197, 94, 0.15)',
        'bubble-purple': 'rgba(168, 85, 247, 0.15)',
        'bubble-blue': 'rgba(59, 130, 246, 0.15)',
      },
      backdropBlur: {
        'xs': '2px',
        'sm': '4px',
        'md': '8px',
        'lg': '12px',
        'xl': '20px',
        '2xl': '40px',
        '3xl': '60px',
      },
      boxShadow: {
        'glow': '0 0 20px rgba(255, 255, 255, 0.3)',
        'glow-sm': '0 0 10px rgba(255, 255, 255, 0.2)',
        'glow-md': '0 0 30px rgba(255, 255, 255, 0.15)',
        'oil-slick': 'inset 0 0 60px rgba(0, 0, 0, 0.5), 0 0 40px rgba(255, 255, 255, 0.05)',
        'glass': '0 8px 32px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.1)',
      },
      animation: {
        'float': 'float 3s ease-in-out infinite',
        'float-slow': 'float 4s ease-in-out infinite',
        'float-fast': 'float 2s ease-in-out infinite',
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        'shimmer': 'shimmer 2s linear infinite',
        'bubble-morph': 'bubbleMorph 0.3s ease-out',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        pulseGlow: {
          '0%, 100%': { opacity: '0.5', transform: 'scale(1)' },
          '50%': { opacity: '1', transform: 'scale(1.05)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        bubbleMorph: {
          '0%': { transform: 'scale(0.8)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
