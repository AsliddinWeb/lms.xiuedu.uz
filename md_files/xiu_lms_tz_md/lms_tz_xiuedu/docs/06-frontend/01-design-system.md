# 01. Design System

## Maqsad

Yagona dizayn tili — ranglar, tipografiya, intervallar, komponentlar. Tailwind CSS ustida qurilgan.

## Ranglar palitrasi

### Primary (asosiy)
```js
// tailwind.config.js
colors: {
  primary: {
    50:  '#EFF6FF',
    100: '#DBEAFE',
    200: '#BFDBFE',
    300: '#93C5FD',
    400: '#60A5FA',
    500: '#3B82F6',  // ASOSIY
    600: '#2563EB',
    700: '#1D4ED8',
    800: '#1E40AF',
    900: '#1E3A8A',
  },
}
```

### Secondary, semantic ranglar

```js
secondary: {
  500: '#10B981',  // yashil — accent
},

success: {
  50:  '#F0FDF4',
  500: '#22C55E',
  600: '#16A34A',
  700: '#15803D',
},

warning: {
  50:  '#FFFBEB',
  500: '#F59E0B',
  600: '#D97706',
  700: '#B45309',
},

danger: {
  50:  '#FEF2F2',
  500: '#EF4444',
  600: '#DC2626',
  700: '#B91C1C',
},

info: {
  500: '#06B6D4',
},

// Neutral (gray)
gray: {
  50:  '#F9FAFB',
  100: '#F3F4F6',
  200: '#E5E7EB',
  300: '#D1D5DB',
  400: '#9CA3AF',
  500: '#6B7280',
  600: '#4B5563',
  700: '#374151',
  800: '#1F2937',
  900: '#111827',
},
```

### Foydalanish

| Maqsad | Rang |
|--------|------|
| Asosiy harakat (CTA) | `primary-500/600` |
| Tasdiqlash, muvaffaqiyat | `success-500` |
| Ogohlantirish | `warning-500` |
| Xato, o'chirish | `danger-500` |
| Matn | `gray-900` (asosiy), `gray-600` (yordamchi) |
| Border | `gray-200/300` |
| Background | `white`, `gray-50` |

### Dark mode
Tailwind `dark:` prefix orqali. Asosiy rang qoladi, lekin background va matn aylantiriladi.

## Tipografiya

### Font family
```css
/* Asosiy: Inter (Latin) + Noto Sans Uzbek */
font-family: 'Inter', 'Noto Sans Uzbek', system-ui, sans-serif;

/* Monospace (kod) */
font-family: 'JetBrains Mono', 'Courier New', monospace;
```

### Type scale (Tailwind classlari)

| Class | Size | Use case |
|-------|------|----------|
| `text-xs` | 12px | Captions, badges |
| `text-sm` | 14px | Helper text, table cells |
| `text-base` | 16px | Body text (default) |
| `text-lg` | 18px | Lead paragraphs |
| `text-xl` | 20px | H4, sections |
| `text-2xl` | 24px | H3 |
| `text-3xl` | 30px | H2 |
| `text-4xl` | 36px | H1 |
| `text-5xl` | 48px | Display |

### Font weights
- `font-normal` (400) — body
- `font-medium` (500) — buttons, links
- `font-semibold` (600) — headings, emphasis
- `font-bold` (700) — h1, brand

### Line heights
- `leading-tight` (1.25) — headings
- `leading-normal` (1.5) — body
- `leading-relaxed` (1.625) — long-form

## Spacing

Tailwind 4px base unit:
- `p-1` = 4px
- `p-2` = 8px
- `p-4` = 16px
- `p-6` = 24px
- `p-8` = 32px
- `p-12` = 48px
- `p-16` = 64px

### Layout intervals
- Card padding: `p-6` (24px)
- Section spacing: `py-12` (48px)
- Container max-width: `max-w-7xl` (1280px)
- Sidebar: `w-64` (256px)

## Borders va shadows

```js
// tailwind.config.js
borderRadius: {
  'sm': '4px',
  'DEFAULT': '6px',
  'md': '8px',
  'lg': '12px',
  'xl': '16px',
  '2xl': '24px',
  'full': '9999px',
},

boxShadow: {
  'sm': '0 1px 2px rgba(0,0,0,0.05)',
  'DEFAULT': '0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06)',
  'md': '0 4px 6px rgba(0,0,0,0.07), 0 2px 4px rgba(0,0,0,0.06)',
  'lg': '0 10px 15px rgba(0,0,0,0.1), 0 4px 6px rgba(0,0,0,0.05)',
  'xl': '0 20px 25px rgba(0,0,0,0.1), 0 10px 10px rgba(0,0,0,0.04)',
}
```

## Breakpoints

| Class | Min width | Use case |
|-------|-----------|----------|
| `sm:` | 640px | Tablet portrait |
| `md:` | 768px | Tablet landscape |
| `lg:` | 1024px | Laptop |
| `xl:` | 1280px | Desktop |
| `2xl:` | 1536px | Large desktop |

## Iconlar

**Heroicons** (Outlined va Solid) + **Lucide** (qo'shimcha).

```vue
<script setup>
import { AcademicCapIcon, BookOpenIcon } from '@heroicons/vue/24/outline'
</script>

<template>
  <AcademicCapIcon class="w-6 h-6 text-primary-500" />
</template>
```

## Animatsiyalar

```js
// tailwind.config.js
extend: {
  animation: {
    'fade-in': 'fadeIn 0.2s ease-out',
    'slide-up': 'slideUp 0.3s ease-out',
    'spin-slow': 'spin 3s linear infinite',
  },
  keyframes: {
    fadeIn: {
      '0%': { opacity: '0' },
      '100%': { opacity: '1' },
    },
    slideUp: {
      '0%': { transform: 'translateY(10px)', opacity: '0' },
      '100%': { transform: 'translateY(0)', opacity: '1' },
    },
  },
},
```

## Tailwind config (to'liq)

```js
// frontend/tailwind.config.js
import { defineConfig } from 'tailwindcss'

export default {
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: { /* ... */ },
        success: { /* ... */ },
        // ... yuqorida
      },
      fontFamily: {
        sans: ['Inter', 'Noto Sans Uzbek', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: { /* ... */ },
      keyframes: { /* ... */ },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
    require('@tailwindcss/aspect-ratio'),
  ],
}
```

## Brendlash

### Logo
- SVG format (scalable)
- Versiyalar: light, dark, monochrome
- Yo'l: `/public/logo.svg`

### Loyiha nomi
- "Oliy LMS" — qisqartma
- "O'zbekiston Oliy Ta'lim Masofaviy O'qitish Platformasi" — to'liq

## Accessibility

- WCAG 2.1 AA minimum
- Min contrast ratio: 4.5:1 (matn)
- Min contrast ratio: 3:1 (UI elementlar)
- Focus halqalari (focus-visible)
- ARIA labels
- Keyboard navigation
- Screen reader test (NVDA, VoiceOver)

## Acceptance kriteriyalar

- [ ] Tailwind config to'liq
- [ ] Ranglar palitrasi
- [ ] Typography scale
- [ ] Iconlar (Heroicons)
- [ ] Animatsiyalar
- [ ] Dark mode support
- [ ] Accessibility (WCAG 2.1 AA)
- [ ] Mobile-first responsive
