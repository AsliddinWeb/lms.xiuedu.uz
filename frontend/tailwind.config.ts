import type { Config } from 'tailwindcss'

/**
 * Wireframe-faithful design system.
 * Reference: md_files/ui_wireframes/lms_ui/assets/styles.css
 *
 * Palette: monochrome shadcn-inspired (foreground = near-black, primary = foreground)
 * Fonts: Geist (sans) + Geist Mono (code/labels) + Instrument Serif (display)
 */
export default {
  content: ['./src/**/*.{vue,js,ts,jsx,tsx,html}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Geist', 'ui-sans-serif', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"Geist Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
        serif: ['"Instrument Serif"', 'Georgia', 'serif'],
      },
      colors: {
        background: 'var(--bg)',
        foreground: 'var(--fg)',
        muted: {
          DEFAULT: 'var(--muted)',
          foreground: 'var(--muted-fg)',
        },
        border: {
          DEFAULT: 'var(--border)',
          strong: 'var(--border-strong)',
        },
        // Mavjud loyiha kodlari (avvalgi UI) sinmasligi uchun "primary" qora
        primary: {
          50: '#fafafa',
          100: '#f4f4f5',
          200: '#e4e4e7',
          300: '#d4d4d8',
          400: '#a1a1aa',
          500: '#71717a',
          600: '#27272a',
          700: '#18181b',
          800: '#0a0a0a',
          900: '#000000',
          DEFAULT: '#0a0a0a',
        },
        success: {
          50: '#f0fdf4',
          200: '#bbf7d0',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
        },
        warning: {
          50: '#fefce8',
          200: '#fde68a',
          500: '#eab308',
          600: '#ca8a04',
          700: '#a16207',
        },
        danger: {
          50: '#fef2f2',
          200: '#fecaca',
          500: '#ef4444',
          600: '#dc2626',
          700: '#b91c1c',
        },
        info: {
          50: '#eff6ff',
          200: '#bfdbfe',
          500: '#3b82f6',
          700: '#1d4ed8',
        },
      },
      letterSpacing: {
        tightest: '-0.04em',
        tight: '-0.025em',
        widest: '0.1em',
      },
      borderRadius: {
        DEFAULT: '6px',
      },
      boxShadow: {
        focus: '0 0 0 3px rgba(0, 0, 0, 0.05)',
      },
    },
  },
  plugins: [],
} satisfies Config
