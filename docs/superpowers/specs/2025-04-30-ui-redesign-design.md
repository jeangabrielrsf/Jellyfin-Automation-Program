# UI Redesign - Glassmorphism Premium

## 2025-04-30

---

## 1. Resumo

Redesign completo do frontend do Jellyfin Automation com estética **Glassmorphism Premium** no estilo **Orgânico Moderno**. Adição de tema claro/escuro com toggle persistente. Foco em profundidade visual, animações fluidas, tipografia distintiva e micro-interações refinadas.

---

## 2. Direção Visual

### Conceito
Interface com glassmorphism elegante — superfícies semi-transparentes com `backdrop-blur`, bordas luminosas sutis, e gradientes de fundo em múltiplas camadas que criam profundidade. O visual transmite **premium + acolhedor**, como um app de curadoria de mídia de alto nível.

### Diferenciação
- Cards glass com elevação e glow no hover
- Gradientes de fundo em camadas com blobs difusos
- Tipografia serif em headings (Playfair Display) contrastando com sans-serif moderna no body (Outfit)
- Animações orchestradas de entrada staggered

---

## 3. Paleta de Cores

### Tema Escuro (default)
- **Fundo base**: `#0f172a` (slate-950)
- **Gradiente de fundo**: camadas suaves de `#1e293b` → `#0f172a` com blobs difusos em `#334155` (20% opacidade)
- **Cards glass**: `rgba(30, 41, 59, 0.6)` com `backdrop-blur: 16px` e borda `rgba(255,255,255,0.08)`
- **Texto primário**: `#f8fafc` (slate-50)
- **Texto secundário**: `#94a3b8` (slate-400)
- **Acento principal**: `#fb923c` (orange-400) — coral/âmbar quente
- **Acento secundário**: `#38bdf8` (sky-400) — azul céu para estados interativos
- **Sucesso**: `#4ade80` (green-400)
- **Erro**: `#f87171` (red-400)

### Tema Claro
- **Fundo base**: `#fafaf9` (stone-50) — branco quente
- **Gradiente de fundo**: camadas de `#f5f5f4` → `#fafaf9` com blobs difusos em `#e7e5e4` (30% opacidade)
- **Cards glass**: `rgba(255, 255, 255, 0.7)` com `backdrop-blur: 16px` e borda `rgba(0,0,0,0.06)`
- **Texto primário**: `#1c1917` (stone-900)
- **Texto secundário**: `#78716c` (stone-500)
- **Acento principal**: `#ea580c` (orange-600)
- **Acento secundário**: `#0284c7` (sky-600)

---

## 4. Tipografia

- **Display/Headings**: *Playfair Display* (serif elegante, Google Fonts) — títulos de página e hero
- **Body/UI**: *Outfit* (geometric sans-serif, Google Fonts) — todo texto de interface
- **Monospace**: *JetBrains Mono* — logs, dados técnicos, timestamps
- **Escala**: ratio 1.25 (major third)
- **Pesos**: headings 700, body 400/500

---

## 5. Layout e Navegação

### Container
- max-width: `1400px`, centralizado
- Padding: `px-6 lg:px-12`

### Header Flutuante
- `position: fixed`, `backdrop-blur-xl`, fundo semi-transparente
- Altura: `72px`
- Contém: logo (Playfair Display 24px weight 700 + ícone play laranja), nav links com ícones Lucide, **toggle de tema** (botão circular sol/lua), user avatar placeholder

### Sidebar (desktop >1280px)
- Colapsável, ícones + labels
- Mobile: header com hamburger menu

### Main Content
- `padding-top: 96px` (compensar header fixo)
- `padding-bottom: 64px`

### Footer
- Minimalista: linha sutil com versão e copyright, centrado, texto muted

### Navegação
- Link ativo: fundo acento laranja 10% opacidade, texto laranja, underline animado (scaleX 0→1)
- Hover: elevação `translateY(-1px)` + glow sutil
- Transição de página: fade-in `translateY(8px)` → `translateY(0)`, 300ms, `cubic-bezier(0.4, 0, 0.2, 1)`

### Grid por Página
- **Home**: hero centralizado + grid cards 3-col (md), 1-col (mobile)
- **Search**: searchbar grande centralizada + grid posters 6-col (lg), 4 (md), 2 (sm)
- **Downloads**: lista vertical com cards expansíveis
- **Settings**: grid 2-col de cards config
- **Logs**: tela cheia com terminal estilizado

---

## 6. Componentes Principais

### Glass Card
- Fundo: `rgba(var(--card-bg), 0.6)` com `backdrop-filter: blur(16px)`
- Borda: `1px solid rgba(var(--border-color), 0.1)`, `border-radius: 16px`
- Sombra: `0 4px 24px rgba(0,0,0,0.08)` (dark: `0 4px 24px rgba(0,0,0,0.3)`)
- Hover: `translateY(-4px)`, sombra aumentada, brilho borda com acento 20% opacidade
- Transição: `all 0.3s cubic-bezier(0.4, 0, 0.2, 1)`

### Media Card (Poster)
- Aspect ratio 2:3, `border-radius: 12px`
- Overlay gradiente inferior: transparente → `rgba(0,0,0,0.8)` com título e metadata
- Hover: zoom imagem `scale: 1.05`, overlay mais visível, botão play aparece no centro
- Loading: shimmer animation

### Button
- **Primário**: fundo laranja, texto branco, `border-radius: 12px`, sombra laranja suave
- **Hover**: brilho intenso, `scale: 1.02`
- **Secundário/Outline**: borda laranja, texto laranja, fundo transparente
- **Ghost**: sem fundo, apenas texto com ícone
- Todos: `transition: all 0.2s ease-out`, active `scale: 0.98`

### SearchBar
- Input grande, centralizado, `border-radius: 16px`, glass effect
- Ícone busca à esquerda, botão busca à direita integrado
- Focus: glow azul sutil, borda pronunciada

### Progress Bar
- Fundo: `rgba(var(--muted), 0.3)`
- Preenchimento: gradiente linear laranja → coral
- Borda arredondada, altura `8px`
- Animação suave de preenchimento

### Badge
- `border-radius: 8px`, padding compacto
- Variantes: default (muted), accent (laranja opaco), outline (borda apenas)
- Texto uppercase, `0.75rem`, weight 600, `letter-spacing: 0.05em`

---

## 7. Micro-interações e Animações

- **Page load**: staggered reveal dos cards — `opacity: 0→1`, `translateY: 20px→0`, delay 50ms incremental por card
- **Theme toggle**: rotação ícone 180° + fade crossover, 400ms
- **Card hover**: elevação + glow, imagem zoom, overlay info slide-up
- **Button press**: `scale: 0.98` no active
- **Toast notifications**: slide-in da direita com glass effect, auto-dismiss com barra de progresso
- **Download progress**: barra com shimmer animado, pulso sutil no ícone de status
- **Nav link**: underline scaleX transform-origin left, ícone `translateY(-2px)`
- **Skeleton loading**: shimmer infinito movendo gradiente horizontal

---

## 8. Tema Claro/Escuro

- Toggle persistente em `localStorage` + `classList` no `<html>`
- Variáveis CSS em `:root` e `.dark` expandidas com novas cores
- Transição de tema: `transition: background-color 0.3s ease, color 0.3s ease` no body
- Fallback: `prefers-color-scheme` detection

---

## 9. Dependências Adicionais

- Google Fonts: Playfair Display, Outfit, JetBrains Mono
- Tailwind CSS já configurado — adicionar classes customizadas
- `tailwindcss-animate` já instalado — expandir keyframes

---

## 10. Arquivos Afetados

- `frontend/src/index.css` — novas variáveis CSS, font imports, keyframes
- `frontend/tailwind.config.js` — extensão de tema, novas cores, keyframes, animations
- `frontend/src/main.tsx` — adicionar ThemeProvider
- `frontend/src/App.tsx` — novo layout com header flutuante, nav redesenhada, theme toggle
- `frontend/src/pages/Home.tsx` — hero + cards redesenhados
- `frontend/src/pages/Search.tsx` — searchbar glass + media cards
- `frontend/src/pages/Downloads.tsx` — cards expansíveis com progresso
- `frontend/src/pages/Settings.tsx` — grid glass cards
- `frontend/src/pages/Logs.tsx` — terminal estilizado
- `frontend/src/components/MediaCard.tsx` — poster com overlay e hover
- `frontend/src/components/SearchBar.tsx` — input glass grande
- `frontend/src/components/TorrentList.tsx` — lista com glass items
- `frontend/src/components/DownloadMonitor.tsx` — progresso com shimmer
- **Novo**: `frontend/src/components/ThemeToggle.tsx` — toggle sol/lua
- **Novo**: `frontend/src/components/Header.tsx` — header flutuante glass
- **Novo**: `frontend/src/context/ThemeContext.tsx` — contexto de tema
