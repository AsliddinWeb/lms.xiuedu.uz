# XIU LMS — Design System

**Manba:** `md_files/ui_wireframes/lms_ui/assets/styles.css`
**Sana:** 2026-05-11

Bu hujjat XIU LMS frontend uchun majburiy dizayn qoidalarini belgilaydi.
Har yangi sahifa yaratishdan oldin shu hujjatni o'qish va wireframe'larga
mos kelishini ta'minlash kerak.

---

## 1. Tipografika

3 ta shrift (Google Fonts orqali):

| Family | Maqsad | Misol |
|---|---|---|
| **Geist** (300–700) | Asosiy UI matni | Body, sarlavhalar, tugmalar |
| **Geist Mono** (400, 500) | Mono metadata | Badge, breadcrumb, label, raqamlar (`tnum`), kategoriyalar, statlar |
| **Instrument Serif** | Hero sarlavhalar (faqat auth/marketing) | Login branding text |

**Font feature settings:** `body { font-feature-settings: 'cv11', 'ss01'; }` — Geist ning stylistic variantlari.
**Statlar uchun:** `font-feature-settings: 'tnum'` — tabular nums (raqamlar bir xil kenglikda).

### Hierarchy
```
.page-title       — 28px, weight 600, letter-spacing -0.025em
.stat-value       — 28px, weight 600, tnum
h3 (card-title)   — 14px, weight 600
body text         — 14px, weight 400
.badge / .mono-tag — 11px, weight 500, Geist Mono, UPPERCASE
.breadcrumb       — 11px, Geist Mono, UPPERCASE, letter-spacing 0.05em
.sidebar-section-title — 10px, Geist Mono, UPPERCASE, letter-spacing 0.1em
```

---

## 2. Ranglar

**Monoxrom shadcn palette** — har sahifada qattiq mos kelishi shart. Blue Tailwind default IShlatilmaydi.

### Light mode
```css
--background: #ffffff
--foreground: #0a0a0a
--muted: #f4f4f5
--muted-foreground: #71717a
--border: #e4e4e7
--border-strong: #d4d4d8
--card: #ffffff
--primary: #18181b           /* Active state fon */
--primary-foreground: #fafafa
--accent: #f4f4f5
--destructive: #dc2626
--success: #16a34a
--warning: #ca8a04
--info: #2563eb              /* Faqat avatar va info marker uchun */

/* Wireframe accents */
--wireframe-bg: #fafafa       /* Sahifa fon (oqdan biroz qoraytirilgan) */
--placeholder: #e4e4e7
--placeholder-text: #a1a1aa
```

### Dark mode (CSS variable swap)
```css
[data-theme="dark"] {
  --background: #09090b
  --foreground: #fafafa
  --muted: #18181b
  --muted-foreground: #a1a1aa
  --border: #27272a
  --border-strong: #3f3f46
  --card: #09090b
  /* ... */
}
```

### Badge varianti ranglari
```css
.badge-success { background: #f0fdf4; border-color: #bbf7d0; color: #15803d; }
.badge-warning { background: #fefce8; border-color: #fde68a; color: #a16207; }
.badge-danger  { background: #fef2f2; border-color: #fecaca; color: #b91c1c; }
.badge-info    { background: #eff6ff; border-color: #bfdbfe; color: #1d4ed8; }
```

---

## 3. Layout

### App Shell (talaba/pedagog/admin asosiy layout)
```
+--------+---------------------------+
| 260px  | topbar (sticky)           |
| side-  +---------------------------+
| bar    | content (max 1400px)      |
| (full  | 32px padding              |
| height,|                           |
| sticky)|                           |
+--------+---------------------------+
```

### Auth Shell (login/register/forgot)
```
+----------------+----------------+
| 50%            | 50%            |
| qora           | oq             |
| (#0a0a0a)      | form           |
| branding       | 400px max      |
| + stats        | centered       |
+----------------+----------------+
```

### Live Class Shell (15-live-class)
```
+------------------------------+
| header (auto)                |
+-------------+----------------+
| 1fr         | 320px          |
| video grid  | side panel     |
| (3fr+1fr    | (chat/people/  |
| thumbs row) |  Q&A)          |
+-------------+----------------+
| controls (auto, center)      |
+------------------------------+
```

### Lesson Player Shell (07-lesson-player)
```
+--------+---------------------------+
| 320px  | topbar (lesson 4.3 / 24)  |
| lesson +---------------------------+
| sidebar| dark video player area    |
|        +---------------------------+
| (modul | materials/izoh/savol      |
| list)  | tabs (light)              |
+--------+---------------------------+
```

---

## 4. Spacing

Konstantalar (8px grid + 4px sub-grid):

```
4px  — gap-1, mb-1
8px  — gap-2, padding-sm
12px — gap-3
16px — gap-4, card padding, content gap
20px — card padding, sidebar padding
24px — gap-6, section spacing
32px — content padding, page-header
48px — auth side padding
```

---

## 5. Komponentlar

### Sidebar
```
.sidebar              — 260px width, 1px border-right, 24px+16px padding, sticky h-100vh
.sidebar-logo         — 28x28 black square icon + bold text + 32px mb
.sidebar-section      — 24px mb
.sidebar-section-title — 10px Geist Mono UPPERCASE, mute, 0–8 padding bottom
.nav-item             — 8x10 padding, 6px radius, 14px font, 500 weight, 10px gap
.nav-item.active      — bg foreground, text background (INVERS — qora fon oq matn)
.nav-item:hover       — bg muted
.nav-icon             — 16x16 SVG, stroke 1.5
.nav-badge            — Geist Mono 11px, muted bg, 4px radius, 1px 6px padding
.nav-item.active .nav-badge — bg rgba(255,255,255,0.15), text background
```

### Topbar
```
.topbar               — 12px 32px padding, 1px border-bottom, sticky top
.topbar-search        — flex 1, max 400px, muted bg, 8x12 padding, 36px left for icon
.topbar-actions       — gap 8px, margin-left auto
.icon-btn             — 36x36 grid, transparent, hover muted
.notification-dot     — 6x6 destructive, top-right
.avatar               — 32x32 round, foreground bg, background text, 12px weight 600
```

**Topbar tartibi (chap → o'ng):**
1. Search input (chap, flex 1, max 400px)
2. Actions: UiLocaleToggle → UiThemeToggle → Notifications bell
3. Vertical separator (`w-px h-6 bg-border`)
4. **UiUserMenu** (dropdown) — avatar + ism + role + chevron

### UiUserMenu (dropdown)

**Maqsad:** Profil va akkaunt amallarini (logout) sidebar'dan ajratib, topbar'dagi user pill bosilganda ochiladigan dropdown'ga ko'chirish (professional admin-panel pattern).

```
Trigger pill:
  avatar (32x32 round) + [ism (12px medium) + role (10px mono uppercase)] + chevron

Dropdown panel (mt-1.5, right-0, w-64):
  Header bo'limi (px-4 py-3, bg-muted/30):
    - Ism (13px semibold)
    - Email (11px mono, muted)
    - Role (10px mono uppercase)
  Items (p-1, gap 0.5):
    - Profile  (icon + label)
    - Security (icon + label)
    - --- divider ---
    - Logout (qizil text-danger-600, danger flag)
```

**Headless UI Menu** + transition (locale toggle bilan bir xil pattern). Items prop array — har sahifa o'z konfiguratsiyasini berishi mumkin.

**Qoida:** Sidebar footer'da Profile va Security **YO'Q** — ular faqat UiUserMenu dropdown'da. Sidebar footer'da faqat wireframe-faithful narsalar: Yordam, Sozlamalar (border-top bilan).

### Cards
```
.card                 — 8px radius, 1px border, oq bg
.card-header          — 16x20 padding, 1px border-bottom
.card-title           — 14px weight 600
.card-body            — 20px padding

.stat-card            — 20px padding, 8px radius, 1px border
.stat-label           — 11px Geist Mono UPPERCASE, mute, 8px mb
.stat-value           — 28px weight 600, tnum
.stat-trend           — 12px, 4px mt, dot bilan
.stat-trend.up        — success
.stat-trend.down      — destructive
```

### Buttons
```
.btn                  — 8x14 padding, 6px radius, 13px weight 500, 8px gap, 1px border
.btn-primary          — foreground bg, background text, hover #27272a
.btn-outline          — background bg, border-strong, hover muted
.btn-ghost            — transparent, hover muted
.btn-sm               — 6x10 padding, 12px font
.btn-lg               — 12x20 padding, 14px font
```

### Inputs
```
.input                — full width, 9x12 padding, 1px border-strong, 6px radius, 13px
.input:focus          — border foreground, shadow rgba(0,0,0,0.05)
.label                — 12px weight 500, 6px mb
.field                — 16px mb
.help-text            — 11px Geist Mono, mute, 4px mt
```

### Tables
```
.table                — full width, collapse, 13px
.table th             — 10x16 padding, 11px Geist Mono UPPERCASE, mute, muted bg, 1px border-bottom
.table td             — 12x16 padding, 1px border-bottom
.table tr:hover td    — muted bg
.table tr:last-child td — no border
```

### Badges
```
.badge                — inline-flex, 4px gap, 2x8 padding, 11px Geist Mono, 4px radius, 1px border
.badge-dot::before    — 6x6 currentColor dot
.badge-success/warning/danger/info — har biri o'z ranglar
```

### Placeholders (wireframe specific)
```
.placeholder          — 45deg diagonal stripe (8px bg-size), dashed border, mono UPPERCASE
.image-placeholder    — muted bg, 1px border, 45deg fine line pattern + center label
.video-placeholder    — dark (#18181b), 16/9 aspect, white play button overlay
```

### Tabs
```
.tabs                 — flex, 4px gap, 1px border-bottom, 24px mb
.tab                  — 10x16 padding, 13px weight 500, mute, transparent
.tab.active           — foreground, 2px border-bottom foreground
.tab:hover            — foreground
```

### Progress
```
.progress             — full width, 6px height, muted bg, 3px radius
.progress-bar         — foreground bg
```

### Course card (wireframe 05)
```
.course-card          — 8px radius, 1px border, oq bg, hover translate-y(-2px)
.course-cover         — 16/9 aspect, muted bg
.course-meta          — 16px padding
.course-category      — 10px Geist Mono UPPERCASE, 0.1em letter-spacing, mute, 8px mb
.course-title         — 14px weight 600, line-height 1.4, 8px mb
.course-stats         — flex, 12px gap, 11px mute, 12px mb
```

---

## 6. Iconlar — wireframe SVG nuqtalari

Har icon **16x16 viewBox, stroke 1.5, fill none**. Wireframe'da aniq path nuqtalari berilgan — har bir nav iconni shu nuqtalardan ko'chirib olish kerak.

### Talaba sidebar
| Nom | SVG path |
|---|---|
| dashboard | `<rect x="2" y="2" w="5" h="5"/><rect x="9" y="2" w="5" h="5"/><rect x="2" y="9" w="5" h="5"/><rect x="9" y="9" w="5" h="5"/>` |
| courses (3-line) | `M2 4h12 M2 8h12 M2 12h8` |
| assignments | `<rect x="3" y="2" w="10" h="12"/><path d="M5 5h6 M5 8h6 M5 11h4"/>` |
| schedule (clock) | `<circle cx="8" cy="8" r="6"/><path d="M8 4v4l2 2"/>` |
| grades (bar chart) | `M2 14V2 M2 14h12 M5 11V7 M8 11V4 M11 11V8` |
| payments | `<rect x="2" y="4" w="12" h="9" rx="1"/><path d="M2 7h12"/>` |
| certificates | `M3 3h10v10H3z` + inner `M6 6h4v4H6z` |
| forum | `M3 4h10 M3 8h10 M3 12h6` |
| messages (envelope) | `M2 4l6 5 6-5 M2 4v8h12V4` |
| help | `<circle cx="8" cy="8" r="6"/><path d="M8 5v3 M8 10v.5"/>` |
| settings (gear) | `<circle cx="8" cy="8" r="2"/><circle cx="8" cy="8" r="6"/>` |

### Pedagog sidebar
| Nom | SVG path |
|---|---|
| my-courses | (=courses) `M2 4h12 M2 8h12 M2 12h8` |
| course-builder | `M8 2v12 M2 8h12` |
| teacher-assignments | `M3 4h10v9H3z M5 7h6 M5 10h4` |
| live (record dot) | `<circle cx="8" cy="8" r="6"/><circle cx="8" cy="8" r="2" fill="currentColor"/>` |
| students | `<circle cx="6" cy="5" r="2"/><circle cx="11" cy="5" r="2"/><path d="M2 13a4 4 0 0 1 8 0 M7 13a4 4 0 0 1 8 0"/>` |
| analytics (=grades) | `M2 14V2 M2 14h12 M5 11V7 M8 11V4 M11 11V8` |
| reports | `M3 3h10v10H3z M6 6h4v4H6z` |

### Admin sidebar
| Nom | SVG path |
|---|---|
| users | `<circle cx="6" cy="5" r="2"/><circle cx="11" cy="5" r="2"/><path d="M2 13a4 4 0 0 1 8 0 M7 13a4 4 0 0 1 8 0"/>` |
| integrations | `<circle cx="8" cy="8" r="3"/><path d="M8 1v3 M8 12v3 M1 8h3 M12 8h3"/>` |
| audit | `M3 3h10v10H3z` |

### Topbar
| Nom | SVG |
|---|---|
| search (12px) | `<circle cx="6" cy="6" r="4"/><path d="m9 9 3 3"/>` |
| notification (bell) | `M3 6a5 5 0 0 1 10 0v4l1 2H2l1-2V6z M6 14a2 2 0 0 0 4 0` |
| messages | `M2 4l6 5 6-5 M2 4v8h12V4` |

---

## 7. CSS feature qoidalari

- **Hover transitions:** `transition: all 0.15s` (umumiy), `0.2s` (transformations)
- **Border radius:** 4px (badge/small), 6px (input/button/sidebar item), 8px (card)
- **Box shadow:** wireframe'da minimal — focus ring (`0 0 0 3px rgba(0,0,0,0.05)`) va hover translate
- **Animations:** `pulse 1.5s ease-in-out infinite` (live dot), `0.15s` transitions
- **Cursor:** `pointer` har clickable element'da

---

## 8. Responsive

```css
@media (max-width: 768px) {
  .app-shell        { grid-template-columns: 1fr; }
  .sidebar          { display: none; }   /* mobile menu kelajakda */
  .stat-grid        { grid-template-columns: repeat(2, 1fr); }
  .auth-page        { grid-template-columns: 1fr; }
  .auth-side        { display: none; }
}

@media (max-width: 1024px) {
  /* live-shell side panel hidden on tablet */
  .live-body        { grid-template-columns: 1fr; }
  .side-panel       { display: none; }
}
```

---

## 9. Qoidalar (har yangi sahifa uchun)

1. **Wireframe-first:** Yangi sahifa yaratmasdan oldin `md_files/ui_wireframes/lms_ui/pages/` ichidan mos wireframe topib o'qish. Wireframe yo'q bo'lsa eng yaqin pattern'ga assign qilish (CRUD list → 17, detail+rubric → 14, kurs grid → 05, va h.k.).
2. **Komponentlar prioriteti:** Shared komponentlar (UiCard, UiBadge, UiTabs, UiCourseCard, UiStatCard, UiBreadcrumb) ishlatish — bir xil CSS qaytarmaslik.
3. **`@apply` vs inline class:** Tailwind `@apply` minimum — wireframe paddings/colors aniq, shuning uchun utility class ko'p ishlatamiz. Ammo bir xil pattern 3+ joyda takrorlansa — komponentga ajratish.
4. **Dark mode majburiy:** Har sahifa CSS variable orqali light va dark mode'da to'g'ri ko'rinishi shart.
5. **i18n majburiy:** Har visible string `t('...')` orqali. 4 ta locale (uz-lat/uz-cyr/ru/en) majburiy.
6. **Icons SVG inline:** Wireframe'da har icon `path` nuqtalari berilgan — `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">` standartiga rioya qilish.
7. **Hard refresh + dev test:** Har vue file o'zgarganda Vite HMR avtomatik, lekin locale o'zgarsa konteyner restart kerak (`docker compose restart frontend-user frontend-admin`).
