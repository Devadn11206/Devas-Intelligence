/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        canvas: '#08090C',
        background: '#08090C',
        obsidian: {
          canvas: '#08090C',
          glass: 'rgba(19, 22, 29, 0.78)',
          elevated: 'rgba(26, 31, 41, 0.88)',
          surface: '#12151D',
          border: 'rgba(212, 175, 55, 0.16)',
          hover: 'rgba(229, 193, 88, 0.38)',
        },
        gold: {
          DEFAULT: '#D4AF37',
          light: '#F3D06B',
          rich: '#E5C158',
          dark: '#AA8828',
          glow: 'rgba(212, 175, 55, 0.35)',
        },
        sapphire: {
          DEFAULT: '#3B82F6',
          light: '#60A5FA',
          glow: 'rgba(59, 130, 246, 0.35)',
        },
        emerald: {
          DEFAULT: '#10B981',
          light: '#34D399',
        },
        alabaster: {
          DEFAULT: '#F8FAFC',
          muted: '#94A3B8',
          dim: '#64748B',
        },
        // Legacy alias maps to luxury palette so any unmapped classes gracefully render in gold/sapphire
        coral: {
          DEFAULT: '#D4AF37',
          light: '#F3D06B',
          dark: '#AA8828',
          glow: 'rgba(212, 175, 55, 0.35)',
        },
        terracotta: {
          DEFAULT: '#E5C158',
          tint: 'rgba(212, 175, 55, 0.12)',
          border: 'rgba(212, 175, 55, 0.16)',
          dark: '#AA8828',
        },
        surface: {
          50: '#232936',
          100: '#1A1F29',
          200: '#12151D',
          300: '#0D0F14',
          card: '#10131A',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
        sans: ['Inter', 'Plus Jakarta Sans', 'system-ui', '-apple-system', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
