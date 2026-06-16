# UI/UX Спецификация: Crypto Arbitrage Dashboard

> **Версия:** 1.0
> **Дата:** Июль 2025
> **Тема:** Dark (по умолчанию), TradingView-стиль
> **Биржи:** Bybit, Binance, KuCoin, Gate.io, Bitget, CoinEx, BingX (7)
> **Frontend:** React 19 + TypeScript + Vite + Tailwind CSS + shadcn/ui + Zustand + Recharts

---

## 1. Общая структура приложения

### 1.1. Layout

```
+-------------------------------------------------------------+
|  Navbar (fixed, height: 56px)                               |
|  [Logo] [Page Title]                    [Status] [UserMenu] |
+--------+-------------------+------------------------------+
|        |                   |                                |
|        |                   |                                |
| Sidebar|  Content Area     |  Right Panel                  |
| (w:    |  (flex: 1)        |  (w: 320px, collapsible)      |
| 240px) |                   |                                |
|        |                   |                                |
|        |                   |                                |
+--------+-------------------+------------------------------+
```

**Layout specs:**

| Параметр | Значение |
|----------|----------|
| Navbar height | 56px |
| Sidebar width (desktop) | 240px |
| Sidebar width (collapsed) | 64px |
| Right panel width | 320px |
| Content max-width | 1440px |
| Content padding | 24px (desktop), 16px (tablet), 12px (mobile) |
| Gap between sections | 24px |
| Border-radius (cards) | 12px |
| Border-radius (buttons) | 8px |
| Border-radius (badges) | 6px |

**Navbar** — `position: fixed`, `z-index: 50`, фон `#0d0d1a` с `border-bottom: 1px solid #1e1e2e`.

**Sidebar** — `position: fixed`, `top: 56px`, фон `#12121f`, `border-right: 1px solid #1e1e2e`. Переключатель collapse внизу sidebar.

**Content Area** — `margin-left: 240px` (или 64px collapsed), `margin-top: 56px`, фон `#0a0a14`, min-height: `calc(100vh - 56px)`.

**Right Panel** — опциональная панель деталей (drawer-стиль), collapsible через кнопку в navbar. Используется на страницах Opportunities и Trades для показа деталей без ухода с текущей страницы.

### 1.2. Навигация (Sidebar Menu Items)

| # | Icon | Label | Route | Badge |
|---|------|-------|-------|-------|
| 1 | `LayoutDashboard` | Dashboard | `/dashboard` | — |
| 2 | `Zap` | Opportunities | `/opportunities` | Live count (зелёный badge) |
| 3 | `ArrowLeftRight` | Trades | `/trades` | — |
| 4 | `BarChart3` | Analytics | `/analytics` | — |
| 5 | `Building2` | Exchanges | `/exchanges` | Warning badge если API не настроен |
| 6 | `Settings` | Settings | `/settings` | Dot badge если есть несохранённые изменения |

**Нижняя секция sidebar:**

| # | Icon | Label | Route |
|---|------|-------|-------|
| 7 | `HelpCircle` | Help & Docs | `/help` |
| 8 | `LogOut` | Logout | `/logout` |

**Sidebar item структура:**
- Height: 40px
- Padding: 8px 16px
- Border-radius: 8px
- Gap между иконкой и текстом: 12px
- Active state: фон `#1a1a2e`, текст `#00d4aa`, иконка `#00d4aa`, левая граница 3px `#00d4aa`
- Hover state: фон `#16162a`
- Transition: `background-color 200ms ease, color 150ms ease`

**Collapse toggle** — иконка `ChevronsLeft`/`ChevronsRight`, positioned absolute bottom, padding 12px.

### 1.3. Адаптивность

| Breakpoint | Ширина | Layout |
|------------|--------|--------|
| Desktop | 1280px+ | Full layout: sidebar 240px + content + optional right panel |
| Tablet | 768px - 1279px | Sidebar collapsed 64px + content, right panel as overlay drawer |
| Mobile | < 768px | Sidebar → hamburger bottom sheet, single column content |

### 1.4. Темы

**Dark theme (по умолчанию):**

| Токен | Значение |
|-------|----------|
| Background (page) | `#0a0a14` |
| Surface (card) | `#12121f` |
| Elevated (modal, dropdown) | `#1a1a2e` |
| Border | `#1e1e2e` |
| Border hover | `#2a2a40` |

**Light theme:**

| Токен | Значение |
|-------|----------|
| Background (page) | `#f8f9fc` |
| Surface (card) | `#ffffff` |
| Elevated (modal, dropdown) | `#ffffff` |
| Border | `#e2e5ef` |
| Border hover | `#c5c9d6` |

**System theme:** автоопределение через `prefers-color-scheme`. Переключатель в Settings → System.

---

## 2. Дизайн-система

### 2.1. Цветовая палитра

#### Primary / Brand

| Токен | HEX | Использование |
|-------|-----|---------------|
| Primary | `#00d4aa` | Основной акцент: активные элементы, положительная динамика, CTA |
| Primary hover | `#00b894` | Hover state primary |
| Primary muted | `rgba(0, 212, 170, 0.15)` | Background для primary badge, subtle highlights |
| Primary glow | `rgba(0, 212, 170, 0.4)` | Glow effects, box-shadow |

#### Secondary

| Токен | HEX | Использование |
|-------|-----|---------------|
| Secondary | `#6366f1` | Вторичный акцент: графики, альтернативные данные |
| Secondary hover | `#5558e0` | Hover state secondary |
| Secondary muted | `rgba(99, 102, 241, 0.15)` | Background для secondary badge |

#### Accent

| Токен | HEX | Использование |
|-------|-----|---------------|
| Accent | `#f59e0b` | Выделение: active trades, warnings, premium |
| Accent hover | `#d97706` | Hover state accent |

#### Semantic Colors

| Токен | HEX | Использование |
|-------|-----|---------------|
| Success | `#22c55e` | Положительный P&L, успешная сделка, WS online |
| Success muted | `rgba(34, 197, 94, 0.15)` | Background success badge |
| Warning | `#f59e0b` | Предупреждение, спред средний, latency высокий |
| Warning muted | `rgba(245, 158, 11, 0.15)` | Background warning badge |
| Danger | `#ef4444` | Отрицательный P&L, ошибка, WS offline, риск |
| Danger muted | `rgba(239, 68, 68, 0.15)` | Background danger badge |
| Info | `#3b82f6` | Информация, подсказки, нейтральный статус |
| Info muted | `rgba(59, 130, 246, 0.15)` | Background info badge |
| Neutral | `#6b7280` | Нейтральный статус, отключено |
| Neutral muted | `rgba(107, 114, 128, 0.15)` | Background neutral badge |

#### Background Colors (Dark Theme)

| Токен | HEX | Использование |
|-------|-----|---------------|
| Page bg | `#0a0a14` | Фон всей страницы |
| Surface | `#12121f` | Фон карточек |
| Surface hover | `#16162a` | Hover на surface |
| Elevated | `#1a1a2e` | Модальные окна, dropdown, popover |
| Elevated hover | `#1e1e35` | Hover на elevated |
| Overlay | `rgba(0, 0, 0, 0.7)` | Backdrop для модалов |
| Input bg | `#0f0f1a` | Фон input полей |
| Input focus | `#12121f` | Фон input в фокусе |

#### Text Colors (Dark Theme)

| Токен | HEX | Использование |
|-------|-----|---------------|
| Text primary | `#f1f5f9` | Основной текст, заголовки |
| Text secondary | `#94a3b8` | Вторичный текст, метки, описания |
| Text muted | `#64748b` | Третичный текст, timestamps, placeholders |
| Text disabled | `#475569` | Неактивный текст |
| Text inverse | `#0a0a14` | Текст на светлых фонах (buttons) |
| Text success | `#22c55e` | Положительные числа |
| Text danger | `#ef4444` | Отрицательные числа |
| Text warning | `#f59e0b` | Предупреждающие числа |

#### Border Colors

| Токен | HEX | Использование |
|-------|-----|---------------|
| Border default | `#1e1e2e` | Стандартные границы |
| Border hover | `#2a2a40` | Hover state границ |
| Border focus | `#00d4aa` | Фокусное состояние |
| Border error | `#ef4444` | Ошибка валидации |

#### Градиенты

| Название | Значение | Использование |
|----------|----------|---------------|
| Gradient primary | `linear-gradient(135deg, #00d4aa 0%, #6366f1 100%)` | Premium badge, hero elements |
| Gradient success | `linear-gradient(135deg, #22c55e 0%, #00d4aa 100%)` | Positive P&L cards |
| Gradient danger | `linear-gradient(135deg, #ef4444 0%, #f59e0b 100%)` | Risk alerts |
| Gradient surface | `linear-gradient(180deg, #12121f 0%, #0d0d1a 100%)` | Card backgrounds |
| Gradient glow primary | `radial-gradient(circle, rgba(0,212,170,0.15) 0%, transparent 70%)` | Subtle glow behind KPI |

### 2.2. Типографика

#### Шрифты

| Роль | Шрифт | Fallback |
|------|-------|----------|
| Primary (UI) | Inter | system-ui, -apple-system, sans-serif |
| Monospace (числа, код) | JetBrains Mono | SF Mono, Consolas, monospace |

**Font stack:**
```css
--font-sans: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
--font-mono: 'JetBrains Mono', 'SF Mono', 'Consolas', monospace;
```

#### Размеры

| Токен | Размер | Line-height | Использование |
|-------|--------|-------------|---------------|
| xs | 12px / 0.75rem | 16px | Теги, timestamps, fine print |
| sm | 13px / 0.8125rem | 18px | Table cells, secondary info |
| base | 14px / 0.875rem | 20px | Body text, inputs, buttons |
| lg | 16px / 1rem | 24px | Subheadings, card titles |
| xl | 20px / 1.25rem | 28px | Section headings |
| 2xl | 24px / 1.5rem | 32px | Page titles |
| 3xl | 30px / 1.875rem | 36px | Hero numbers (KPI) |
| 4xl | 36px / 2.25rem | 40px | Large KPI values |

#### Веса

| Токен | Вес | Использование |
|-------|-----|---------------|
| Regular | 400 | Body text, descriptions |
| Medium | 500 | Labels, button text |
| Semibold | 600 | Headings, card titles, active nav |
| Bold | 700 | Hero numbers, page titles |

**Цифры:** всегда `font-variant-numeric: tabular-nums` — предотвращает "прыгание" чисел при обновлении.

### 2.3. Spacing

#### Grid System

- 12-колоночная grid
- Gutter: 24px (desktop), 16px (tablet), 12px (mobile)
- Max container width: 1440px

#### Scale

| Токен | Значение |
|-------|----------|
| space-1 | 4px |
| space-2 | 8px |
| space-3 | 12px |
| space-4 | 16px |
| space-5 | 20px |
| space-6 | 24px |
| space-8 | 32px |
| space-10 | 40px |
| space-12 | 48px |
| space-16 | 64px |

#### Border Radius Scale

| Токен | Значение |
|-------|----------|
| radius-sm | 4px |
| radius-md | 8px |
| radius-lg | 12px |
| radius-xl | 16px |
| radius-full | 9999px |

#### Shadows

| Токен | Значение |
|-------|----------|
| shadow-sm | `0 1px 2px rgba(0,0,0,0.3)` |
| shadow-md | `0 4px 12px rgba(0,0,0,0.4)` |
| shadow-lg | `0 8px 24px rgba(0,0,0,0.5)` |
| shadow-glow-primary | `0 0 20px rgba(0, 212, 170, 0.3)` |
| shadow-glow-danger | `0 0 20px rgba(239, 68, 68, 0.3)` |
| shadow-inset | `inset 0 2px 4px rgba(0,0,0,0.3)` |

### 2.4. Компоненты

#### Button

| Variant | Background | Text | Border | Hover | Active |
|---------|-----------|------|--------|-------|--------|
| Primary | `#00d4aa` | `#0a0a14` | none | `#00b894` | `#009e7d` |
| Secondary | `#1a1a2e` | `#f1f5f9` | `1px solid #2a2a40` | `#1e1e35` | `#222240` |
| Ghost | transparent | `#94a3b8` | none | `rgba(255,255,255,0.05)` | `rgba(255,255,255,0.08)` |
| Danger | `#ef4444` | `#ffffff` | none | `#dc2626` | `#b91d1d` |
| Outline | transparent | `#00d4aa` | `1px solid #00d4aa` | `rgba(0,212,170,0.1)` | `rgba(0,212,170,0.15)` |

**Sizes:**

| Size | Height | Padding | Font-size |
|------|--------|---------|-----------|
| sm | 32px | 12px 16px | 13px |
| md (default) | 40px | 16px 20px | 14px |
| lg | 48px | 20px 28px | 16px |
| icon-sm | 32px | 8px | — |
| icon-md | 40px | 10px | — |

**States:**
- Loading: spinner (16px) вместо текста, opacity 0.7, cursor wait
- Disabled: opacity 0.4, cursor not-allowed
- Focus: `box-shadow: 0 0 0 2px rgba(0, 212, 170, 0.3)`

**Animation:** `transform 150ms ease, background-color 150ms ease`

#### Card

```
+-------------------------------+
| [Header: title + optional    |
|  action button]               |
+-------------------------------+
|                               |
| [Content]                     |
|                               |
+-------------------------------+
| [Footer: optional]           |
+-------------------------------+
```

| Variant | Background | Border | Shadow |
|---------|-----------|--------|--------|
| Default | `#12121f` | `1px solid #1e1e2e` | none |
| Elevated | `#1a1a2e` | `1px solid #2a2a40` | `shadow-md` |
| Flat | `#12121f` | none | none |

**Specs:**
- Border-radius: 12px
- Padding: 20px (default), 16px (compact)
- Header border-bottom: `1px solid #1e1e2e` (если есть header)
- Header padding-bottom: 16px
- Margin-bottom header→content: 16px

**Hover (elevated):** `transform: translateY(-2px)`, `shadow: shadow-lg`, transition `200ms ease`

#### Table

| Часть | Spec |
|-------|------|
| Header bg | `#0f0f1a` |
| Header text | `#94a3b8`, font-weight 500, font-size 13px |
| Header height | 40px |
| Row height | 52px |
| Row bg default | transparent |
| Row bg hover | `rgba(255,255,255,0.03)` |
| Row bg selected | `rgba(0, 212, 170, 0.08)` |
| Cell padding | 12px 16px |
| Border-bottom row | `1px solid #1e1e2e` |
| Border-radius wrapper | 12px |
| Border wrapper | `1px solid #1e1e2e` |

**Sortable header:** иконка `ArrowUpDown` (12px, `#475569`), при hover — `#94a3b8`. При сортировке — `#00d4aa`.

**Pagination:**
- Height: 48px
- Page buttons: 32x32px, border-radius 6px
- Active page: bg `#00d4aa`, text `#0a0a14`
- Rows per page select: sm размер

#### Form Inputs

**Text input:**
- Height: 40px
- Background: `#0f0f1a`
- Border: `1px solid #1e1e2e`
- Border-radius: 8px
- Padding: 0 14px
- Font: 14px, `#f1f5f9`
- Placeholder: `#475569`
- Focus: border `#00d4aa`, `box-shadow: 0 0 0 3px rgba(0, 212, 170, 0.15)`
- Error: border `#ef4444`, `box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.15)`
- Transition: `border-color 150ms ease, box-shadow 150ms ease`

**Select (dropdown):**
- Те же размеры что и text input
- Chevron icon справа (16px, `#64748b`)
- Dropdown menu: bg `#1a1a2e`, border `1px solid #2a2a40`, border-radius 8px, shadow `shadow-lg`
- Item hover: bg `#222240`
- Item selected: bg `rgba(0, 212, 170, 0.1)`, text `#00d4aa`

**Switch (toggle):**
- Track: 44x24px, border-radius 12px
- Off: bg `#2a2a40`
- On: bg `#00d4aa`
- Thumb: 20x20px, border-radius 10px, bg `#ffffff`, shadow `shadow-sm`
- Transition: `background-color 150ms ease`
- Thumb transition: `transform 150ms cubic-bezier(0.4, 0, 0.2, 1)`

**Slider:**
- Track height: 6px, border-radius 3px
- Track bg: `#1e1e2e`
- Filled bg: `#00d4aa`
- Thumb: 18x18px, border-radius 9px, bg `#00d4aa`, border `2px solid #ffffff`
- Thumb hover: scale 1.15, `shadow-glow-primary`

**Textarea:**
- Min-height: 80px
- Остальные спецификации как у text input
- Resize: vertical

#### Badge

| Variant | Background | Text |
|---------|-----------|------|
| Success | `rgba(34, 197, 94, 0.15)` | `#22c55e` |
| Warning | `rgba(245, 158, 11, 0.15)` | `#f59e0b` |
| Danger | `rgba(239, 68, 68, 0.15)` | `#ef4444` |
| Info | `rgba(59, 130, 246, 0.15)` | `#3b82f6` |
| Neutral | `rgba(107, 114, 128, 0.15)` | `#6b7280` |
| Primary | `rgba(0, 212, 170, 0.15)` | `#00d4aa` |

**Specs:**
- Height: 22px
- Padding: 0 10px
- Border-radius: 6px
- Font: 12px, font-weight 500
- Border: `1px solid` matching text color at 30% opacity

#### Modal / Dialog

**Overlay:**
- Background: `rgba(0, 0, 0, 0.7)`
- Backdrop-filter: `blur(4px)`
- Animation: `opacity 200ms ease`

**Modal window:**
- Background: `#1a1a2e`
- Border: `1px solid #2a2a40`
- Border-radius: 16px
- Shadow: `shadow-lg`
- Max-width: 560px (default), 720px (lg), 420px (sm)
- Padding: 24px
- Animation: `opacity 200ms ease, transform 200ms cubic-bezier(0.16, 1, 0.3, 1)`
- Initial: `opacity: 0, transform: scale(0.96) translateY(10px)`
- Final: `opacity: 1, transform: scale(1) translateY(0)`

**Header:** title (18px, semibold), close button (top-right, 32x32, ghost variant, иконка X)

**Footer:** action buttons, right-aligned, gap 12px

#### Toast / Notification

```
+------------------------------------------+
| [Icon] Title              [Close]        |
| Description                              |
+------------------------------------------+
```

| Variant | Icon | Border-left |
|---------|------|-------------|
| Success | CheckCircle (20px, `#22c55e`) | 3px solid `#22c55e` |
| Error | XCircle (20px, `#ef4444`) | 3px solid `#ef4444` |
| Warning | AlertTriangle (20px, `#f59e0b`) | 3px solid `#f59e0b` |
| Info | Info (20px, `#3b82f6`) | 3px solid `#3b82f6` |

**Specs:**
- Background: `#1a1a2e`
- Border: `1px solid #2a2a40`
- Border-radius: 10px
- Shadow: `shadow-lg`
- Padding: 14px 18px
- Min-width: 320px, max-width: 420px
- Position: top-right, gap 8px между toasts
- Auto-dismiss: 5000ms (success/info), 8000ms (error/warning)
- Progress bar: 2px внизу, цвет соответствует variant, анимация уменьшения
- Entry animation: `slideInRight 300ms cubic-bezier(0.16, 1, 0.3, 1)`
- Exit animation: `slideOutRight 200ms ease`

#### Tooltip

- Background: `#1e1e35`
- Text: `#f1f5f9`, 13px
- Padding: 6px 12px
- Border-radius: 6px
- Shadow: `shadow-sm`
- Arrow: 6px, bg `#1e1e35`
- Animation: `fadeIn 150ms ease`
- Delay: 400ms

#### Tabs

| Variant | Spec |
|---------|------|
| Default | Пилл-стиль, bg `#12121f`, active bg `#1a1a2e`, active text `#00d4aa` |
| Underline | Нижняя граница 2px, active border `#00d4aa`, active text `#f1f5f9` |

**Specs:**
- Height: 36px
- Padding: 0 16px
- Font: 14px, font-weight 500
- Gap между табами: 4px
- Transition: `all 150ms ease`

#### Dropdown Menu

- Background: `#1a1a2e`
- Border: `1px solid #2a2a40`
- Border-radius: 10px
- Shadow: `shadow-lg`
- Min-width: 180px
- Padding: 6px
- Item height: 36px
- Item padding: 0 12px
- Item border-radius: 6px
- Item hover: bg `#222240`
- Separator: `1px solid #1e1e2e`, margin 6px 0
- Animation: `opacity 100ms ease, transform 100ms ease`, origin top

#### Date Picker

- Input: как text input + иконка Calendar (16px, `#64748b`)
- Calendar popup: bg `#1a1a2e`, border `1px solid #2a2a40`, border-radius 12px
- Day cell: 36x36px, border-radius 8px
- Selected: bg `#00d4aa`, text `#0a0a14`
- Today: border `1px solid #00d4aa`, text `#00d4aa`
- Hover: bg `#222240`
- Range: bg `rgba(0, 212, 170, 0.1)`
- Month/year selector: dropdown inside calendar

#### Search Input

- Height: 40px
- Background: `#0f0f1a`
- Border: `1px solid #1e1e2e`
- Border-radius: 8px (или 20px для rounded variant)
- Padding: 0 14px 0 40px (под иконку)
- Search icon: 16px, `#475569`, position absolute left 14px
- Clear button: X icon (14px), appears при наличии текста
- Focus: border `#00d4aa`

#### Skeleton (Loading States)

- Background: `linear-gradient(90deg, #1a1a2e 25%, #222240 50%, #1a1a2e 75%)`
- Background-size: 200% 100%
- Animation: `shimmer 1.5s ease-in-out infinite`
- Border-radius: 6px (default), 12px (card), 4px (text line)
- Keyframes shimmer: `background-position: 200% 0`

**Skeleton patterns:**
- Text line: height 14-16px, width 60-100%
- Card: full width, height 120px
- Avatar: 40x40px, border-radius 20px
- Table row: 52px height, 4-6 columns

---

## 3. Страницы

### 3.1. Login Page

#### Layout

```
+------------------+--------------------------+
|                  |                          |
|   Brand Panel    |    Login Form            |
|   (left 45%)     |    (right 55%)           |
|                  |                          |
|   [Logo]         |    [Title]               |
|   [Tagline]      |    [Subtitle]            |
|   [Feature       |                          |
|    bullets]      |    [Email input]         |
|   [Gradient      |    [Password input]      |
|    bg]           |    [Remember me]         |
|                  |    [Forgot password?]    |
|   Abstract       |                          |
|   crypto         |    [Login Button]        |
|   illustration   |                          |
|   (subtle        |    [Divider]             |
|   animated)      |    [SSO options]         |
|                  |                          |
+------------------+--------------------------+
```

**Left panel specs:**
- Background: gradient `linear-gradient(160deg, #0a0a14 0%, #12121f 40%, #1a1a2e 100%)`
- Radial glow: `radial-gradient(circle at 30% 50%, rgba(0,212,170,0.08) 0%, transparent 60%)`
- Padding: 64px
- Content vertically centered

**Right panel specs:**
- Background: `#0a0a14`
- Form max-width: 400px, centered
- Padding: 48px

#### Поля

**Email:**
- Label: "Email Address"
- Placeholder: "you@example.com"
- Type: email
- Validation: required, email format
- Auto-focus on page load

**Password:**
- Label: "Password"
- Placeholder: "Enter your password"
- Type: password
- Toggle visibility: иконка Eye / EyeOff (16px, `#64748b`)
- Validation: required, min 8 characters

**Remember me:**
- Checkbox + label "Remember me for 30 days"
- Default: checked

**Forgot password:**
- Ссылка справа от Remember me
- Color: `#00d4aa`, hover: underline

#### Кнопки

**Primary Login:**
- Full width, height 48px
- Text: "Sign In"
- Variant: primary, size lg
- Loading state при submit

#### Валидация

| Поле | Правило | Сообщение об ошибке |
|------|---------|---------------------|
| Email | Required | "Email is required" |
| Email | Valid format | "Please enter a valid email" |
| Password | Required | "Password is required" |
| Password | Min 8 chars | "Password must be at least 8 characters" |

**Валидация в реальном времени:** blur на поле + debounce 300ms для email format.

#### Ошибки

- Invalid credentials: toast error "Invalid email or password"
- Account locked: toast warning "Account temporarily locked. Try again in 15 minutes."
- Server error: toast error "Something went wrong. Please try again."
- Rate limited: toast warning "Too many attempts. Please wait before trying again."

**Form-level ошибка:** inline banner под заголовком формы (danger variant), если пришла ошибка от API.

#### Анимации

| Элемент | Анимация | Длительность | Easing |
|---------|----------|--------------|--------|
| Left panel | fadeIn + slideInLeft | 600ms | `cubic-bezier(0.16, 1, 0.3, 1)` |
| Form | fadeIn + slideInRight | 600ms | `cubic-bezier(0.16, 1, 0.3, 1)` |
| Input focus | glow pulse | 300ms | ease |
| Login button loading | scale 0.98 + spinner | 200ms | ease |
| Brand illustration | subtle floating | infinite 6s | `ease-in-out` |

---

### 3.2. Dashboard Page

#### Layout

```
Page Title: "Dashboard"
Subtitle: "Real-time arbitrage monitoring"

Row 1: KPI Cards (4 cards, grid-cols-4 desktop, 2 tablet, 1 mobile)
Row 2: Exchange Status (7 mini-cards) + Mini P&L Chart
Row 3: Top 5 Opportunities table + Last 5 Trades table
```

#### KPI Cards (4 cards)

| # | Title | Value Format | Trend | Icon | Color |
|---|-------|-------------|-------|------|-------|
| 1 | Total P&L | `+$1,247.50` или `-$45.20` | +12.5% vs yesterday | TrendingUp / TrendingDown | success/danger |
| 2 | Active Opportunities | `23` | Live count | Zap | primary |
| 3 | Today's Trades | `8` | Win rate 75% | ArrowLeftRight | info |
| 4 | Best Spread | `0.47%` (BTC/USDT) | Binance → Bybit | BarChart3 | accent |

**KPI Card specs:**
- Background: `#12121f`
- Border: `1px solid #1e1e2e`
- Border-radius: 12px
- Padding: 20px
- Min-height: 120px

**Internal layout:**
```
[Icon (top-right, 20x20, color variant)]
[Label (13px, #94a3b8, medium)]
[Value (28px, bold, color variant)] — font-mono, tabular-nums
[Trend (12px, #64748b)] — стрелка + процент + "vs yesterday"
```

**Hover:** border `#2a2a40`, `shadow: shadow-md`, transition 200ms.

**Animation:**
- Value: count-up animation от 0 до значения, длительность 800ms, easing `cubic-bezier(0.16, 1, 0.3, 1)`
- Cards: stagger fadeIn (каждая через 100ms после предыдущей)

#### Exchange Status Panel

**7 mini-cards в grid (7 columns desktop, 4 tablet, 2 mobile):**

Каждая карточка биржи:
- Background: `#12121f`
- Border: `1px solid #1e1e2e`
- Border-radius: 10px
- Padding: 16px
- Min-height: 100px

**Internal layout:**
```
[Logo placeholder: первые 2 буквы имени в круге 36px, bg #1a1a2e, font 14px bold]
[Exchange name: 14px semibold, #f1f5f9]
[WS Status: пульсирующая точка 8px + текст]
[Latency: значок Wi-Fi + "24ms"]
[Balance: "~$12.4K" или "N/A"]
```

**WS Status dot:**
- Online: `#22c55e`, пульсация (scale 1 → 1.5 → 1, opacity 1 → 0.5 → 1), 2s infinite
- Offline: `#ef4444`, статичная
- Connecting: `#f59e0b`, мигающая (opacity 0.3 → 1), 1s infinite

**Hover:** показывать tooltip с полной информацией (last connected, error count, API status).

#### Mini P&L Chart

- Recharts AreaChart
- Размер: full width of its container, height 200px
- Данные: последние 24 часа ( aggregated по часу )
- Area: gradient fill от `rgba(0, 212, 170, 0.3)` к `transparent`
- Line: stroke `#00d4aa`, width 2px
- Grid: horizontal only, stroke `#1e1e2e`, strokeDasharray "3 3"
- X-axis: часы (00:00 - 23:00), font 11px, `#475569`
- Y-axis: USD значения, font 11px, `#475569`
- Tooltip: bg `#1a1a2e`, border `#2a2a40`, border-radius 8px, формат `$1,247.50`

**Animation:** area chart reveal слева направо, 1200ms, `cubic-bezier(0.16, 1, 0.3, 1)`

#### Top 5 Opportunities Table

**Заголовок:** "Top Opportunities" + badge с общим количеством + ссылка "View All →"

**Колонки:**

| Колонка | Ширина | Формат |
|---------|--------|--------|
| Pair | flex | BTC/USDT (жирный) |
| Spread | 80px | `0.47%` с цветовой индикацией |
| Buy | 100px | Bybit `$67,245.00` |
| Sell | 100px | Binance `$67,561.50` |
| Profit | 80px | `+$24.50` |

**Цветовая индикация спреда:**
- `> 0.30%`: text `#22c55e` (green)
- `0.15% - 0.30%`: text `#f59e0b` (yellow)
- `< 0.15%`: text `#64748b` (gray)

**Auto-refresh:** данные обновляются каждые 500ms (WebSocket). Нет спиннера — данные просто меняются с микро-анимацией (cell flash).

**Row flash on update:**
- При изменении значения в ячейке: фон `rgba(0, 212, 170, 0.05)` на 300ms, затем fade out
- Transition: `background-color 300ms ease`

#### Last 5 Trades

**Заголовок:** "Recent Trades" + ссылка "View All →"

**Колонки:**

| Колонка | Ширина | Формат |
|---------|--------|--------|
| Time | 80px | "14:32:05" |
| Pair | flex | BTC/USDT |
| Type | 60px | "Buy"/"Sell" badge |
| P&L | 80px | `+$12.50` / `-$3.20` (цветом) |
| Status | 80px | Completed / Pending badge |

**Badge для Status:**
- Completed: success badge
- Pending: warning badge
- Failed: danger badge

---

### 3.3. Opportunities Page

#### Layout

```
Page Title: "Arbitrage Opportunities"
Subtitle: "Real-time cross-exchange spreads"

[Toolbar Row]
[Table]
[Footer: pagination + last updated]
```

#### Toolbar

**Слева:**
- Заголовок: "Opportunities" (20px, semibold)
- Badge: активное количество (обновляется в реальном времени)
- Auto-refresh indicator: spinner + "Updated 2s ago"

**Фильтры:**

| Фильтр | Тип | Опции |
|--------|-----|-------|
| Exchange | Multi-select | All, Bybit, Binance, KuCoin, Gate.io, Bitget, CoinEx, BingX |
| Pair | Multi-select | All, BTC/USDT, ETH/USDT, BTC/USDC, ETH/USDC, ETH/BTC |
| Min Spread | Slider | 0.05% — 1.00% (step 0.05%) |
| Status | Select | All, Active, Expired |

**Кнопки справа:**
- Sound toggle: иконка Volume2 / VolumeX (вкл/выкл звуковое оповещение)
- Refresh: иконка RefreshCw (manual refresh)
- Settings: иконка Sliders (открывает drawer с расширенными фильтрами)

#### Таблица

**Колонки:**

| # | Колонка | Ширина | Выравнивание | Формат |
|---|---------|--------|-------------|--------|
| 1 | Pair | 140px | left | BTC/USDT (14px semibold) |
| 2 | Buy Exchange | 120px | left | Лого + имя биржи |
| 3 | Sell Exchange | 120px | left | Лого + имя биржи |
| 4 | Spread % | 100px | right | `0.47%` с цветовой индикацией |
| 5 | Buy Price | 130px | right | `$67,245.00` (font-mono) |
| 6 | Sell Price | 130px | right | `$67,561.50` (font-mono) |
| 7 | Est. Profit | 110px | right | `+$24.50` (зелёный) / `-$5.00` (красный) |
| 8 | Status | 100px | center | Badge |
| 9 | Actions | 80px | center | Кнопки |

**Цветовая индикация Spread %:**
- `> 0.30%`: bg `rgba(34, 197, 94, 0.15)`, text `#22c55e`, font-weight 600
- `0.15% - 0.30%`: bg `rgba(245, 158, 11, 0.15)`, text `#f59e0b`, font-weight 500
- `< 0.15%`: text `#64748b`, font-weight 400

**Status badge:**
- Active: primary badge (пульсирующая зелёная точка 6px слева)
- Expired: neutral badge
- Executed: success badge

**Actions:**
- Eye icon: просмотр деталей (открывает right panel drawer)
- Bell icon: подписаться на уведомления по этой паре

**Row highlight:**
- При наведении: bg `rgba(255,255,255,0.03)`
- При спреде > порога (настроенному в Settings): левая граница 3px `#00d4aa`

**Row update animation:**
- При изменении значения спреда: cell bg flash (цвет в зависимости от направления: зелёный если спред вырос, красный если упал)
- Flash длительность: 400ms
- New row: slideDown + fadeIn, 300ms
- Removed row: slideUp + fadeOut, 200ms

**Sound notification:**
- При появлении новой возможности со спредом > порога: звуковой сигнал (короткий beep)
- Toggle в toolbar включает/выключает
- Дополнительно: browser notification (если разрешено)

#### Empty State

- Иконка: Search (48px, `#475569`)
- Title: "No opportunities found"
- Description: "Try adjusting your filters or wait for new arbitrage events."
- Action: "Reset Filters" кнопка

#### Right Panel (Detail Drawer)

**Trigger:** клик на Eye icon в строке
**Width:** 400px
**Animation:** slideInRight 300ms `cubic-bezier(0.16, 1, 0.3, 1)`

**Content:**
```
[Header: Pair name + close button]
[Price comparison card]
  - Buy: Exchange, Price, Timestamp
  - Sell: Exchange, Price, Timestamp
  - Spread: % + absolute
[Order book preview: top 5 bids/asks]
[Historical spread sparkline: last 1 hour]
[Actions: "Paper Trade" button, "Notify Me" toggle]
```

---

### 3.4. Trades Page

#### Layout

```
Page Title: "Trade History"
Subtitle: "Virtual/paper trades log"

[Toolbar with filters]
[Table]
[Pagination + Export]
```

#### Toolbar / Filters

| Фильтр | Тип | Опции |
|--------|-----|-------|
| Date Range | DatePicker | Last 24h, Last 7d, Last 30d, Custom |
| Exchange | Select | All, Bybit, Binance, KuCoin, Gate.io, Bitget, CoinEx, BingX |
| Pair | Select | All, BTC/USDT, ETH/USDT, etc. |
| Status | Multi-select | All, Completed, Pending, Failed, Cancelled |
| P&L | Select | All, Profit, Loss |

**Поиск:** по ID сделки или паре

#### Таблица

| # | Колонка | Ширина | Формат |
|---|---------|--------|--------|
| 1 | ID | 80px | `#TR-0042` (font-mono, 12px, `#64748b`) |
| 2 | Time | 100px | `14:32:05` + дата (12px, `#64748b`) |
| 3 | Pair | 100px | BTC/USDT |
| 4 | Buy Ex | 100px | Bybit (badge) |
| 5 | Sell Ex | 100px | Binance (badge) |
| 6 | Buy Price | 120px | `$67,245.00` (font-mono) |
| 7 | Sell Price | 120px | `$67,561.50` (font-mono) |
| 8 | Size | 100px | `0.5 BTC` |
| 9 | Spread | 80px | `0.47%` |
| 10 | P&L | 100px | `+$24.50` (success) / `-$5.20` (danger), font-weight 600 |
| 11 | Status | 100px | Badge |

**Status badge:**
- Completed: success
- Pending: warning (с анимацией пульсации)
- Failed: danger
- Cancelled: neutral

**P&L форматирование:**
- Положительный: `#22c55e`, prefix `+`, font-weight 600
- Отрицательный: `#ef4444`, prefix `-`, font-weight 600
- Нулевой: `#64748b`

#### Pagination

- Размер страницы: 10, 25, 50, 100 (select)
- Страница: числа + prev/next
- Info: "Showing 1-25 of 156 trades"

#### Export CSV

- Кнопка: иконка Download + "Export CSV"
- При клике: генерируется CSV с учётом текущих фильтров
- Toast: "CSV export started" → "Download ready"
- Формат имени файла: `trades_2025-07-15_2025-07-22.csv`

#### Detail View (Drawer)

**Trigger:** клик на строку таблицы
**Width:** 480px

**Content:**
```
[Header: Trade ID + Status badge + Close]
[Timeline: Created → Detected → Executed → Completed]
[Details Grid: 2 columns]
  - Pair, Type, Buy Exchange, Sell Exchange
  - Buy Price, Sell Price, Size, Spread
  - P&L (gross), Fees (breakdown), P&L (net)
  - Execution time, Slippage
[Raw Data: collapsible JSON of API responses]
[Actions: "Re-run Simulation" button]
```

#### Empty State

- Иконка: ArrowLeftRight (48px, `#475569`)
- Title: "No trades yet"
- Description: "Trades will appear here when arbitrage opportunities are executed. Start with paper trading in Settings."
- Action: "Go to Settings" кнопка (outline variant)

---

### 3.5. Analytics Page

#### Layout

```
Page Title: "Analytics"
Subtitle: "Performance insights & statistics"

[Date Range Picker + Presets]

Row 1: Statistics Cards (6 cards)
Row 2: P&L Chart (full width) + Cumulative P&L Chart (full width)
Row 3: Trades Per Day (half) + Exchange Distribution Pie (half)
Row 4: Pair Distribution Pie (half) + Heatmap (half)
```

#### Date Range Picker

**Presets (chip buttons):**
- Today
- Last 7 Days
- Last 30 Days
- Last 90 Days
- Custom

**Custom range:** Date picker popup с двумя полями (start / end)

**Active preset:** bg `#00d4aa`, text `#0a0a14`
**Inactive:** bg `#1a1a2e`, text `#94a3b8`

#### Statistics Cards (6 cards)

| # | Title | Value | Subtitle | Icon |
|---|-------|-------|----------|------|
| 1 | Win Rate | `68.5%` | 47 wins / 22 losses | Target |
| 2 | Avg Profit/Trade | `+$15.40` | Per successful trade | TrendingUp |
| 3 | Sharpe Ratio | `1.85` | Annualized | Activity |
| 4 | Max Drawdown | `-3.2%` | Worst consecutive loss | TrendingDown |
| 5 | Profit Factor | `2.14` | Gross profit / gross loss | BarChart3 |
| 6 | Total Trades | `69` | This period | ArrowLeftRight |

**Card specs:**
- Background: `#12121f`
- Icon container: 40x40px, border-radius 10px, bg `rgba(0,212,170,0.1)`, icon 20px `#00d4aa`
- Value: 24px, bold, font-mono
- Subtitle: 12px, `#64748b`

**Sharpe Ratio цветовая индикация:**
- `> 2.0`: `#22c55e` (excellent)
- `1.0 - 2.0`: `#00d4aa` (good)
- `0.5 - 1.0`: `#f59e0b` (moderate)
- `< 0.5`: `#ef4444` (poor)

**Max Drawdown:** всегда `#ef4444`

#### P&L Over Time (Area Chart)

- Recharts AreaChart
- Height: 320px
- Данные: P&L по каждой сделке (точки) + линия тренда
- X-axis: дата/время
- Y-axis: P&L в USD
- Area: gradient от `rgba(0, 212, 170, 0.2)` к `transparent`
- Line: `#00d4aa`, 2px
- Positive bars: `#22c55e` (subtle)
- Negative bars: `#ef4444` (subtle)
- Grid: `#1e1e2e`, horizontal only
- Tooltip: detailed (date, trades count, total P&L)
- Brush component для zoom по времени

#### Cumulative P&L (Line Chart)

- Recharts LineChart
- Height: 280px
- Линия: stroke `#6366f1`, width 2.5px, dot радиус 4px
- Area fill: gradient от `rgba(99, 102, 241, 0.15)` к `transparent`
- Reference line: y=0, stroke `#475569`, strokeDasharray
- Tooltip: cumulative value + daily change

#### Trades Per Day (Bar Chart)

- Recharts BarChart
- Height: 280px
- Bar: fill `#1a1a2e`, stroke `#2a2a40`, border-radius 4px top
- Hover bar: fill `#00d4aa`
- X-axis: дни
- Y-axis: количество сделок
- Max value bar: glow effect `shadow-glow-primary`

#### Exchange Distribution (Pie Chart)

- Recharts PieChart
- Height: 280px
- Цвета:
  - Bybit: `#00d4aa`
  - Binance: `#6366f1`
  - KuCoin: `#f59e0b`
  - Gate.io: `#3b82f6`
  - Bitget: `#22c55e`
  - CoinEx: `#ef4444`
  - BingX: `#8b5cf6`
- Donut style (inner radius 60%)
- Center label: "By Exchange"
- Legend: справа, горизонтальные chips
- Active sector: slightly expanded (outerRadius + 8px)
- Tooltip: процент + абсолютное значение

#### Pair Distribution (Pie Chart)

- Аналогично Exchange Distribution
- Цвета: градиенты primary palette

#### Heatmap (Best Hours/Days)

- Custom grid component (не Recharts)
- Grid: 24 колонки (часы) × 7 строк (дни недели)
- Cell size: зависит от контейнера, min 32px
- Cell border-radius: 4px
- Gap: 2px
- Цветовая шкала (количество сделок / P&L):
  - 0: `#12121f`
  - 1-2: `rgba(0, 212, 170, 0.2)`
  - 3-5: `rgba(0, 212, 170, 0.4)`
  - 6-10: `rgba(0, 212, 170, 0.6)`
  - 10+: `rgba(0, 212, 170, 0.9)`
- Hover: tooltip с точными значениями
- X-axis labels: 00, 04, 08, 12, 16, 20
- Y-axis labels: Mon, Tue, Wed, Thu, Fri, Sat, Sun

---

### 3.6. Exchanges Page

#### Layout

```
Page Title: "Exchange Connections"
Subtitle: "Manage your 7 exchange API connections"

[Info banner: "API keys are encrypted at rest" + lock icon]

Grid: 7 cards (3 columns desktop, 2 tablet, 1 mobile)
```

#### Exchange Card

**Каждая карточка:**

```
+----------------------------------+
| [Logo 40px] [Name]      [Toggle] |
| Bybit                             |
|                                   |
| [dot] WebSocket: Online          |
| [wifi] Latency: 24ms              |
| [wallet] Balance: ~$12,400       |
| [key] API: Configured             |
|                                   |
| [Test] [Edit] [Delete]           |
+----------------------------------+
```

**Card specs:**
- Background: `#12121f`
- Border: `1px solid #1e1e2e`
- Border-radius: 12px
- Padding: 20px
- Min-height: 200px

**Logo:**
- Container: 44x44px, border-radius 10px, bg `#1a1a2e`
- Если нет лого: текст (первые 2 буквы), 16px bold, `#00d4aa`

**Toggle Switch:**
- Position: top-right
- Вкл/выкл биржи из мониторинга

**Status items (вертикальный список, gap 8px):**

| Item | Icon | Online | Offline | Warning |
|------|------|--------|---------|---------|
| WebSocket | Circle | `#22c55e` dot + "Online" | `#ef4444` + "Offline" | `#f59e0b` + "Connecting..." |
| Latency | Wifi | `<50ms` green | — | `>200ms` yellow |
| Balance | Wallet | `$12,400` | "N/A" | "Error fetching" |
| API Key | Key | "Configured" green | "Not set" red | "Invalid" yellow |

**Action buttons (bottom, gap 8px):**
- "Test": secondary button, sm (проверяет соединение)
- "Edit": secondary button, sm (открывает модал)
- "Delete": ghost button, sm, danger hover (удаляет ключи)

**Warning state:**
- Если API keys не настроены: вся карточка border `#f59e0b`, bg overlay `rgba(245, 158, 11, 0.03)`
- Badge: "Setup Required" warning badge

#### Edit API Keys Modal

**Trigger:** кнопка "Edit"
**Size:** sm (420px)

**Content:**
```
[Header: "Configure {Exchange}" + logo]
[Description: "Enter your API credentials. Keys are encrypted."]

[Form:]
- API Key: text input + HelpCircle tooltip
- API Secret: password input
- Passphrase (if required): password input
  [опционально, показывается для KuCoin]

[Checkboxes:]
- [x] Read-only mode (recommended)
- [x] IP Whitelist enabled

[Buttons:]
- [Cancel] [Save & Test]
```

**Validation:**
- API Key: required, min 10 chars
- API Secret: required, min 10 chars
- Проверка при Save: test connection API endpoint

**Success:** toast "Connection successful!" → карточка обновляется
**Error:** inline error под полем + toast "Connection failed. Check your API keys."

#### Test Connection Flow

1. Клик "Test" → button loading state
2. API запрос на backend (POST /api/exchanges/{id}/test)
3. Backend проверяет соединение (ping + balance fetch)
4. Result:
   - Success: toast "Bybit: Connected (24ms)" + status обновляется
   - Error: toast "Bybit: Connection failed — Invalid API key"

#### Animation

- Cards: stagger fadeIn, 80ms delay между карточками
- Status dot: пульсация 2s infinite для Online
- Toggle: slide 150ms
- Test button: loading spinner внутри кнопки

---

### 3.7. Settings Page

#### Layout

```
Page Title: "Settings"
Subtitle: "Configure your arbitrage system"

+-------------+------------------------------+
| Sidebar Nav | Content Area                 |
| (w: 200px)  |                              |
|             | [Settings Form]              |
| - Trading   |                              |
| - Notif.    |                              |
| - Risk      |                              |
| - System    |                              |
| - Account   |                              |
|             |                              |
+-------------+------------------------------+
```

**Settings sidebar (nested):**
- Width: 200px
- Background: transparent (встроен в основной content)
- Items: вертикальный список
- Active: text `#00d4aa`, левая граница 3px `#00d4aa`
- Font: 14px, font-weight 500

#### Tab 1: Trading

**Section: Spread Detection**

| Setting | Type | Default | Range |
|---------|------|---------|-------|
| Minimum Spread Threshold | Slider + number input | 0.30% | 0.05% — 2.00% |
| Maximum Spread (cap) | Slider + number input | 5.00% | 1.00% — 10.00% |
| Spread Buffer | Slider | 0.05% | 0.01% — 0.20% |

**Slider specs:**
- Track: как в дизайн-системе
- Number input справа от slider: width 80px
- Единица измерения: `%`
- Tooltip на slider thumb: текущее значение

**Section: Trade Execution**

| Setting | Type | Default | Options |
|---------|------|---------|---------|
| Trade Mode | Radio group | Paper Trading | Paper Trading, Live Trading |
| Trade Size | Number input | 100 | Min 10, Max 100000, unit USDT |
| Max Positions | Number input | 5 | Min 1, Max 20 |
| Max Daily Trades | Number input | 20 | Min 1, Max 100 |

**Radio group:**
- Paper Trading: описание "Simulate trades without real funds (recommended for testing)"
- Live Trading: описание "Execute real trades with your exchange balances" + warning badge "Advanced"

**Section: Advanced**

| Setting | Type | Default |
|---------|------|---------|
| Slippage Tolerance | Slider | 0.10% |
| Order Timeout | Number input | 2000 (ms) |
| Retry Attempts | Number input | 3 |
| Retry Delay | Number input | 500 (ms) |

#### Tab 2: Notifications

**Section: Telegram**

| Setting | Type | Default |
|---------|------|---------|
| Bot Token | Password input | empty |
| Chat ID | Text input | empty |
| [Test Message] button | — | — |

**Help text:** "Create a bot with @BotFather and get your chat ID from @userinfobot"

**Test flow:**
1. Заполнены token + chat ID
2. Клик "Test Message" → loading
3. Backend отправляет тестовое сообщение
4. Success: "Test message sent! Check your Telegram."
5. Error: "Failed to send message. Check your Bot Token and Chat ID."

**Section: Notification Events**

| Event | Toggle | Default |
|-------|--------|---------|
| New opportunity (spread > threshold) | Switch | On |
| Trade executed | Switch | On |
| Trade failed | Switch | On |
| Daily summary | Switch | On |
| Exchange disconnected | Switch | On |
| Risk limit reached | Switch | On |

**Section: Browser Notifications**

| Setting | Type | Default |
|---------|------|---------|
| Enable browser notifications | Switch | Off |
| [Request Permission] button | — | — |

#### Tab 3: Risk

**Section: Daily Limits**

| Setting | Type | Default | Range |
|---------|------|---------|-------|
| Max Daily Loss | Number input | 500 | 0 — 10000, unit USDT |
| Max Daily Trades | Number input | 20 | 1 — 100 |
| Max Consecutive Losses | Number input | 5 | 1 — 20 |

**Section: Position Limits**

| Setting | Type | Default | Range |
|---------|------|---------|-------|
| Max Position Size | Number input | 1000 | 10 — 50000, unit USDT |
| Max Position % of Balance | Slider | 10% | 1% — 50% |

**Section: Kill Switch**

| Setting | Type | Default |
|---------|------|---------|
| Auto-stop on daily loss limit | Switch | On |
| Auto-stop on consecutive losses | Switch | On |
| Pause trading on high latency (>500ms) | Switch | Off |

**Warning banner:**
- Background: `rgba(239, 68, 68, 0.08)`
- Border: `1px solid rgba(239, 68, 68, 0.2)`
- Icon: AlertTriangle
- Text: "Risk settings are critical for protecting your capital. Review carefully before enabling live trading."

#### Tab 4: System

| Setting | Type | Default | Options |
|---------|------|---------|---------|
| Theme | Select | Dark | Dark, Light, System |
| Language | Select | English | English, Russian |
| Timezone | Select | UTC | UTC, Auto-detect, Custom list |
| Data Retention | Select | 30 days | 7 days, 30 days, 90 days, 1 year |
| Auto-refresh interval | Select | 500ms | 100ms, 500ms, 1000ms, 5000ms |
| Sound alerts | Switch | On | — |

#### Tab 5: Account

**Section: Profile**

| Setting | Type | Notes |
|---------|------|-------|
| Email | Display only | Не редактируется |
| Role | Badge | Admin / User |
| Member since | Display only | Дата регистрации |

**Section: Security**

| Setting | Type | Notes |
|---------|------|-------|
| Current Password | Password input | Required for changes |
| New Password | Password input | Min 8 chars, strength indicator |
| Confirm Password | Password input | Must match |
| [Change Password] button | Primary | — |

**Password strength indicator:**
- 4 сегмента (Weak → Fair → Good → Strong)
- Colors: danger → warning → info → success
- Criteria: length, uppercase, number, special char

**Section: Sessions**

| Column | Format |
|--------|--------|
| Device | "Chrome on macOS" |
| Location | "Tbilisi, GE" |
| Last Active | "2 hours ago" |
| Status | "Current session" badge или active dot |
| Action | "Revoke" button (danger ghost) |

#### Auto-save / Save

- **Auto-save:** каждое поле сохраняется автоматически через debounce 1000ms
- **Индикатор:** в правом верхнем углу content area
  - Saving: spinner + "Saving..."
  - Saved: check icon + "Saved" (исчезает через 3s)
  - Error: X icon + "Failed to save"

---

## 4. Интерактивность и анимации

### 4.1. Page Transitions

**Route change:**
- Outgoing page: fadeOut 100ms
- Incoming page: fadeIn 200ms + slideUp 10px
- Easing: `cubic-bezier(0.16, 1, 0.3, 1)`

**Implementation:** CSS transitions через React Router location change.

### 4.2. Loading States

**Initial page load:**
- Full-page skeleton
- Navbar: загружается мгновенно
- Sidebar: загружается мгновенно
- Content: skeleton cards/table в layout страницы

**Data refresh:**
- Overlay spinner (centered, 32px) на текущем контенте
- Или: inline skeleton replacement для обновляемых секций

**Skeleton specs:**
```css
.skeleton {
  background: linear-gradient(90deg, #1a1a2e 25%, #222240 50%, #1a1a2e 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

### 4.3. Real-time Updates (WebSocket)

**Connection status (navbar):**
- Dot indicator 8px в navbar
- Green: connected
- Yellow: reconnecting (мигание 1s)
- Red: disconnected

**Tooltip on hover:** "Connected (latency: 24ms)" / "Reconnecting... (attempt 3)" / "Disconnected"

**Data update patterns:**

| Тип данных | Частота | Анимация |
|------------|---------|----------|
| Opportunities | 100-500ms | Cell flash (300ms), row slide |
| Prices/tickers | 100ms | Cell flash green/red (200ms) |
| Exchange status | 5s | Dot pulse, status text fade |
| P&L metrics | 1s | Count-up (600ms) |
| Trades | On event | Row slideDown + fadeIn |

**Cell flash animation:**
```css
@keyframes cellFlashGreen {
  0% { background-color: rgba(34, 197, 94, 0.2); }
  100% { background-color: transparent; }
}

@keyframes cellFlashRed {
  0% { background-color: rgba(239, 68, 68, 0.2); }
  100% { background-color: transparent; }
}
```

Duration: 300ms, easing: ease-out

### 4.4. Notifications (Toast)

**System events → Toast mapping:**

| Event | Type | Title | Duration |
|-------|------|-------|----------|
| New opportunity (spread > threshold) | success | "Arbitrage: BTC/USDT 0.47%" | 5000ms |
| Trade executed | success | "Trade #TR-0042 executed" | 4000ms |
| Trade failed | error | "Trade #TR-0043 failed: timeout" | 8000ms |
| Exchange disconnected | warning | "Binance: WebSocket disconnected" | 6000ms |
| Exchange reconnected | success | "Binance: Reconnected (24ms)" | 4000ms |
| Daily limit reached | warning | "Daily loss limit reached — trading paused" | 10000ms |
| Settings saved | success | "Settings saved" | 3000ms |

### 4.5. Micro-interactions

| Элемент | Trigger | Animation | Duration | Easing |
|---------|---------|-----------|----------|--------|
| Button | Hover | bg color change | 150ms | ease |
| Button | Click | scale(0.97) | 100ms | ease |
| Button | Release | scale(1) | 150ms | `cubic-bezier(0.34, 1.56, 0.64, 1)` (spring) |
| Card | Hover | translateY(-2px), shadow-md | 200ms | ease |
| Card | Click | scale(0.99) | 100ms | ease |
| Table row | Hover | bg rgba(255,255,255,0.03) | 150ms | ease |
| Nav item | Hover | bg #16162a | 150ms | ease |
| Nav item | Active | border-left slideIn | 200ms | `cubic-bezier(0.16, 1, 0.3, 1)` |
| Badge | Appearance | scale(0.8) → scale(1) | 200ms | `cubic-bezier(0.34, 1.56, 0.64, 1)` |
| Input | Focus | border glow | 200ms | ease |
| Toggle | Click | thumb slide + track color | 150ms | `cubic-bezier(0.4, 0, 0.2, 1)` |
| Modal | Open | fadeIn + scale + slideUp | 200ms | `cubic-bezier(0.16, 1, 0.3, 1)` |
| Modal | Close | fadeOut + scale + slideDown | 150ms | ease |
| Drawer | Open | slideInRight | 300ms | `cubic-bezier(0.16, 1, 0.3, 1)` |
| Drawer | Close | slideOutRight | 200ms | ease |
| Tooltip | Show | fadeIn | 150ms | ease |
| Dropdown | Open | fadeIn + slideDown 4px | 100ms | ease |
| Toast | Enter | slideInRight | 300ms | `cubic-bezier(0.16, 1, 0.3, 1)` |
| Toast | Exit | slideOutRight + fadeOut | 200ms | ease |
| Icon button | Hover | scale(1.1), color change | 150ms | ease |
| Status dot | Pulse | scale + opacity | 2000ms | ease-in-out, infinite |
| Number (KPI) | Update | count-up | 600-800ms | `cubic-bezier(0.16, 1, 0.3, 1)` |
| Copy to clipboard | Click | check icon → revert | 2000ms | ease |

### 4.6. Error States (Fallback UI)

**Global error boundary:**
- Full-screen overlay
- Иконка: AlertTriangle (48px, `#f59e0b`)
- Title: "Something went wrong"
- Description: error message (technical details в collapsible)
- Actions: "Reload Page" (primary), "Go to Dashboard" (secondary)

**Section-level error:**
- Inline banner внутри карточки/секции
- Background: `rgba(239, 68, 68, 0.08)`
- Border: `1px solid rgba(239, 68, 68, 0.2)`
- Icon: XCircle + error text
- Action: "Retry" button

**Network error (WebSocket):**
- Banner под navbar
- Background: `rgba(245, 158, 11, 0.1)`
- Border-bottom: `1px solid rgba(245, 158, 11, 0.2)`
- Text: "Connection unstable. Reconnecting... (attempt 3/5)"
- Progress bar: анимированная полоса

**Empty data (not error):**
- Centered в контейнере
- Иконка: 48px, `#475569`
- Title: 16px, `#94a3b8`
- Description: 14px, `#64748b`
- Optional action button

---

## 5. Responsive Design

### 5.1. Desktop (1280px+)

- Full layout: sidebar 240px + content + optional right panel 320px
- Grid: 4 KPI cards, 3 exchange cards per row, full table
- Charts: side by side (2 per row)
- All features accessible

### 5.2. Tablet (768px - 1279px)

- Sidebar collapsed 64px (только иконки)
- Content padding: 16px
- Grid: 2 KPI cards per row, 2 exchange cards per row
- Table: horizontal scroll с sticky first column
- Charts: stacked (1 per row)
- Right panel: overlay drawer (не side-by-side)

### 5.3. Mobile (< 768px)

- Sidebar: скрыт, hamburger menu → bottom sheet
- Bottom navbar: 5 иконок (Dashboard, Opportunities, Trades, Exchanges, Menu)
- Content padding: 12px
- Single column layout
- KPI cards: stacked (1 per row), compact (min-height 90px)
- Exchange cards: stacked
- Table: карточки вместо таблицы (card-based UI)
- Charts: stacked, height 240px
- Filters: bottom sheet
- Modals: full-screen

### 5.4. Что скрывается / упрощается

| Feature | Desktop | Tablet | Mobile |
|---------|---------|--------|--------|
| Sidebar | Full 240px | Collapsed 64px | Hidden (bottom nav) |
| Right panel | Side-by-side 320px | Overlay drawer | Full-screen modal |
| KPI cards | 4 per row | 2 per row | 1 per row |
| Exchange cards | 3-4 per row | 2 per row | 1 per row |
| Table columns | All visible | Horizontal scroll | Card-based |
| Charts side-by-side | Yes | Stacked | Stacked |
| Filters toolbar | Inline | Inline + dropdown | Bottom sheet |
| Settings sidebar | Nested sidebar | Tabs | Tabs |
| Export CSV | Button | Button | Menu item |

---

## 6. User Flows

### 6.1. Flow 1: Первый вход → настройка бирж → запуск мониторинга

```
1. Login Page → авторизация
   ↓
2. Dashboard (empty state)
   ├── Banner: "Setup your exchanges to start monitoring"
   └── CTA: "Connect Exchanges"
   ↓
3. Exchanges Page
   ├── 7 карточек со статусом "Setup Required"
   ├── Клик "Edit" на первой бирже
   ├── Ввод API Key + Secret
   ├── Клик "Save & Test"
   ├── Успех: статус "Online"
   └── Повтор для остальных бирж
   ↓
4. Settings Page → Trading tab
   ├── Установка min spread (0.30%)
   ├── Trade Mode: Paper Trading
   ├── Trade Size: $100
   └── Авто-сохранение
   ↓
5. Settings Page → Notifications tab
   ├── Ввод Telegram Bot Token
   ├── Ввод Chat ID
   ├── Клик "Test Message"
   └── Успех: сообщение в Telegram
   ↓
6. Dashboard
   ├── Статусы бирж: все Online
   ├── KPI cards: начинают обновляться
   ├── Opportunities: появляются записи
   └── Уведомления: приходят в Telegram
```

**Время на первоначальную настройку:** 10-15 минут

### 6.2. Flow 2: Обнаружение арбитража → paper trade → уведомление

```
1. Система мониторит 7 бирж по WebSocket (100-500ms)
   ↓
2. Scanner обнаруживает спред > threshold
   ├── Backend логирует opportunity
   ├── WebSocket broadcast на фронтенд
   └── Telegram notification отправляется
   ↓
3. Dashboard обновляется
   ├── KPI: Active Opportunities +1
   ├── Opportunities table: новая строка (slideDown animation)
   └── Spread cell: green flash
   ↓
4. Paper Trade (auto-execution)
   ├── Backend симулирует buy + sell
   ├── Trade записывается в БД
   └── Toast: "Paper trade executed: BTC/USDT +$24.50"
   ↓
5. Trades Page
   ├── Новая строка: Pending → Completed
   └── P&L обновляется
   ↓
6. Analytics
   ├── P&L chart: новая точка
   ├── Win Rate пересчитывается
   └── Stats cards обновляются
```

**Latency весь flow:** < 500ms от обнаружения до отображения

### 6.3. Flow 3: Аналитика → экспорт → корректировка настроек

```
1. Analytics Page
   ├── Выбор Date Range (Last 30 Days)
   ├── Просмотр графиков и статистики
   └── Обнаружение: win rate ниже ожидаемого
   ↓
2. Детальный анализ
   ├── Heatmap: лучшие часы для торговли
   ├── Exchange distribution: какая биржа даёт наибольший P&L
   └── Pair distribution: какие пары наиболее прибыльны
   ↓
3. Экспорт данных
   ├── Trades Page
   ├── Применение фильтров (прибыльные пары)
   ├── Клик "Export CSV"
   └── Скачивание файла
   ↓
4. Корректировка настроек
   ├── Settings → Trading
   ├── Уменьшение min spread (0.30% → 0.20%)
   ├── Увеличение trade size ($100 → $200)
   └── Сохранение (auto-save)
   ↓
5. Мониторинг результатов
   ├── Dashboard: наблюдение за метриками
   └── Telegram: уведомления об изменениях
```

---

## 7. Дополнительный функционал (выдающий продукт)

### 7.1. Что сделает продукт лучше конкурентов

| Фича | Конкуренты (Hummingbot и др.) | Наш продукт |
|------|------------------------------|-------------|
| Интерфейс | CLI или базовый Streamlit | Профессиональный React-дашборд |
| Paper Trading | Есть, но через CLI | Полная визуализация в UI |
| Real-time | Ограниченная | WebSocket <100ms, cell flash анимации |
| Multi-exchange monitoring | Требует ручной настройки | 7 бирж "из коробки" с карточками статуса |
| Mobile experience | Нет | Адаптивный дашборд + Telegram уведомления |
| Аналитика | Минимальная | Полный набор графиков + heatmap |
| UX первого запуска | Нужны технические знания | Wizard пошаговой настройки |
| Risk management | Базовый | Визуальные лимиты + kill switch |

### 7.2. Предложения по улучшению UX

1. **Onboarding Wizard** — для первого входа: пошаговый гид (Connect API → Set Threshold → Start Monitoring), 3 шага с progress indicator

2. **Opportunity Alert Overlay** — при спреде > 1%: центрированный modal с ярким градиентом + звуковой сигнал + кнопка быстрого действия

3. **Command Palette** (`Cmd+K` / `Ctrl+K`) — быстрый поиск по страницам, парам, биржам, настройкам. Как в VS Code / Linear

4. **Customizable Dashboard** — drag-and-drop KPI cards, возможность выбрать какие метрики показывать, resize charts

5. **Trade Simulation Replay** — возможность "переиграть" конкретную сделку с изменёнными параметрами (what-if analysis)

6. **Price Alert Widget** — мини-виджет в sidebar с текущими ценами на избранные пары (как в TradingView watchlist)

7. **Dark/Live Mode Toggle в 1 клик** — иконка в navbar для мгновенного переключения

8. **Copy-to-clipboard** для всех значений (клик на число → скопировано → checkmark tooltip)

9. **Keyboard Shortcuts** — таблица шорткатов (`?` для открытия), навигация по страницам через цифры

10. **Smart Defaults** — авто-подбор порога спреда на основе исторических данных за первую неделю

### 7.3. Roadmap фич (post-MVP)

| Приоритет | Фича | Описание | ETA |
|-----------|------|----------|-----|
| P1 | Multi-user support | Роли (admin, trader, viewer), команды | Month 2 |
| P1 | Webhook notifications | Внешние webhook для интеграций | Month 2 |
| P1 | CSV import trades | Импорт исторических сделок | Month 2 |
| P2 | Triangular arbitrage | Треугольный арбитраж в UI | Month 3 |
| P2 | Funding rate arbitrage | Спот-перпетуал спреды | Month 3 |
| P2 | Custom strategies | UI для настройки кастомных стратегий | Month 3 |
| P2 | Backtesting | Историческое тестирование стратегий | Month 3-4 |
| P3 | DEX integration | Uniswap, PancakeSwap | Month 4-5 |
| P3 | AI insights | ML-подсказки по оптимальным настройкам | Month 5-6 |
| P3 | Mobile app | React Native приложение | Month 6+ |
| P3 | White-label | Кастомизация брендинга | Month 6+ |

---

## Приложение A: Иконки (Lucide React)

| Назначение | Иконка | Размер |
|------------|--------|--------|
| Dashboard | `LayoutDashboard` | 20px |
| Opportunities | `Zap` | 20px |
| Trades | `ArrowLeftRight` | 20px |
| Analytics | `BarChart3` | 20px |
| Exchanges | `Building2` | 20px |
| Settings | `Settings` | 20px |
| Help | `HelpCircle` | 20px |
| Logout | `LogOut` | 20px |
| Search | `Search` | 16px |
| Close | `X` | 16px |
| Eye / View | `Eye` | 16px |
| Eye Off | `EyeOff` | 16px |
| Bell | `Bell` | 16px |
| Check | `Check` | 16px |
| Chevron | `ChevronDown` / `ChevronRight` | 16px |
| Refresh | `RefreshCw` | 16px |
| Download | `Download` | 16px |
| Wifi | `Wifi` | 14px |
| Wallet | `Wallet` | 14px |
| Key | `Key` | 14px |
| Circle (status) | `Circle` | 8px |
| Trending Up | `TrendingUp` | 16px |
| Trending Down | `TrendingDown` | 16px |
| Target | `Target` | 20px |
| Activity | `Activity` | 20px |
| Alert Triangle | `AlertTriangle` | 16-20px |
| Info | `Info` | 16px |
| Lock | `Lock` | 16px |
| Calendar | `Calendar` | 16px |
| Sliders | `SlidersHorizontal` | 16px |
| Volume | `Volume2` / `VolumeX` | 16px |
| User | `User` | 16px |
| Trash | `Trash2` | 16px |
| Edit | `Pencil` | 16px |
| Copy | `Copy` | 14px |
| External Link | `ExternalLink` | 14px |
| Arrow Up/Down (sort) | `ArrowUpDown` | 12px |
| Chevron Left/Right | `ChevronsLeft` / `ChevronsRight` | 18px |
| Menu (hamburger) | `Menu` | 20px |

## Приложение B: Zustand Store Structure

```typescript
interface AppStore {
  // Theme
  theme: 'dark' | 'light' | 'system';
  setTheme: (theme: 'dark' | 'light' | 'system') => void;

  // Sidebar
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;

  // Notifications
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;

  // WebSocket
  wsStatus: 'connected' | 'connecting' | 'disconnected';
  wsLatency: number;

  // Opportunities
  opportunities: Opportunity[];
  opportunitiesFilter: OpportunitiesFilter;
  setOpportunitiesFilter: (filter: Partial<OpportunitiesFilter>) => void;

  // Trades
  trades: Trade[];
  tradesFilter: TradesFilter;
  setTradesFilter: (filter: Partial<TradesFilter>) => void;

  // Settings
  settings: Settings;
  updateSetting: (key: string, value: unknown) => void;

  // Selected exchange detail
  selectedExchangeId: string | null;
  setSelectedExchangeId: (id: string | null) => void;
}
```

## Приложение C: Breakpoints Reference

| Breakpoint | Tailwind | CSS | Описание |
|------------|----------|-----|----------|
| sm | `sm:` | `640px` | Малые устройства |
| md | `md:` | `768px` | Tablet |
| lg | `lg:` | `1024px` | Desktop small |
| xl | `xl:` | `1280px` | Desktop (primary) |
| 2xl | `2xl:` | `1536px` | Desktop large |

**Primary breakpoint:** 1280px (xl) — полный layout

---

*Спецификация подготовлена на основе исследований рынка крипто-арбитража и технологического стека. Дизайн-решения ориентированы на профессиональных трейдеров с опытом работы в TradingView / Bloomberg Terminal.*
