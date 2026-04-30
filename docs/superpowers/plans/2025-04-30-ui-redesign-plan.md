# UI Redesign Glassmorphism Premium Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the complete Glassmorphism Premium UI redesign with light/dark theme toggle, new typography, animations, and redesigned all pages.

**Architecture:** Build a ThemeContext for persistent light/dark mode. Redesign global styles (CSS vars, fonts, keyframes). Create new glassmorphic Header and ThemeToggle components. Redesign every page component with glass cards, staggered animations, and improved UX. Update Tailwind config with new colors and animations.

**Tech Stack:** React 18, Tailwind CSS, shadcn/ui, Lucide React, TanStack Query, React Router, Google Fonts (Playfair Display, Outfit, JetBrains Mono)

---

## File Structure

| File | Action | Responsibility |
|------|--------|--------------|
| `frontend/src/index.css` | Modify | CSS variables (light/dark), font imports, keyframes, base styles |
| `frontend/tailwind.config.js` | Modify | Extended colors, keyframes, animations, fontFamily |
| `frontend/src/context/ThemeContext.tsx` | Create | Theme state management, localStorage, prefers-color-scheme |
| `frontend/src/components/ThemeToggle.tsx` | Create | Sun/moon toggle button with rotation animation |
| `frontend/src/components/Header.tsx` | Create | Floating glass header with nav, logo, theme toggle |
| `frontend/src/App.tsx` | Modify | New layout with Header, main content area, page transitions |
| `frontend/src/main.tsx` | Modify | Wrap with ThemeProvider |
| `frontend/src/pages/Home.tsx` | Modify | Hero + feature cards with glassmorphism |
| `frontend/src/components/SearchBar.tsx` | Modify | Large glass search input with focus glow |
| `frontend/src/components/MediaCard.tsx` | Modify | Poster card with overlay, hover zoom, play button |
| `frontend/src/pages/Search.tsx` | Modify | Search page with glass searchbar + poster grid |
| `frontend/src/components/TorrentList.tsx` | Modify | Glass torrent items with metadata badges |
| `frontend/src/components/DownloadMonitor.tsx` | Modify | Progress cards with shimmer animation |
| `frontend/src/pages/Downloads.tsx` | Modify | Downloads page with glass progress cards |
| `frontend/src/pages/Settings.tsx` | Modify | Settings grid with glass config cards |
| `frontend/src/pages/Logs.tsx` | Modify | Styled terminal-like log viewer |

---

### Task 1: Foundation — CSS Variables, Fonts, and Tailwind Config

**Files:**
- Modify: `frontend/src/index.css`
- Modify: `frontend/tailwind.config.js`

- [ ] **Step 1: Add Google Fonts import and update CSS variables**

Replace the entire content of `frontend/src/index.css`:

```css
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600;700&family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 30 6% 98%;
    --foreground: 24 10% 10%;
    --card: 0 0% 100%;
    --card-foreground: 24 10% 10%;
    --popover: 0 0% 100%;
    --popover-foreground: 24 10% 10%;
    --primary: 24 95% 42%;
    --primary-foreground: 0 0% 100%;
    --secondary: 30 6% 94%;
    --secondary-foreground: 24 10% 10%;
    --muted: 30 6% 94%;
    --muted-foreground: 24 6% 46%;
    --accent: 30 6% 94%;
    --accent-foreground: 24 10% 10%;
    --destructive: 0 84% 60%;
    --destructive-foreground: 0 0% 100%;
    --border: 24 6% 88%;
    --input: 24 6% 88%;
    --ring: 24 95% 42%;
    --radius: 0.75rem;
    --success: 142 71% 45%;
    --success-foreground: 0 0% 100%;
    --warning: 38 92% 50%;
    --warning-foreground: 0 0% 100%;
    --info: 199 89% 48%;
    --info-foreground: 0 0% 100%;
  }

  .dark {
    --background: 222 47% 6%;
    --foreground: 210 40% 98%;
    --card: 217 33% 17%;
    --card-foreground: 210 40% 98%;
    --popover: 217 33% 17%;
    --popover-foreground: 210 40% 98%;
    --primary: 27 96% 61%;
    --primary-foreground: 222 47% 6%;
    --secondary: 217 33% 17%;
    --secondary-foreground: 210 40% 98%;
    --muted: 217 33% 17%;
    --muted-foreground: 215 20% 65%;
    --accent: 217 33% 17%;
    --accent-foreground: 210 40% 98%;
    --destructive: 0 62% 50%;
    --destructive-foreground: 210 40% 98%;
    --border: 217 33% 22%;
    --input: 217 33% 22%;
    --ring: 27 96% 61%;
    --radius: 0.75rem;
    --success: 142 71% 55%;
    --success-foreground: 222 47% 6%;
    --warning: 38 92% 60%;
    --warning-foreground: 222 47% 6%;
    --info: 199 89% 58%;
    --info-foreground: 222 47% 6%;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  html {
    scroll-behavior: smooth;
  }
  body {
    @apply bg-background text-foreground antialiased;
    font-family: 'Outfit', sans-serif;
    transition: background-color 0.3s ease, color 0.3s ease;
  }
  h1, h2, h3, h4, h5, h6 {
    font-family: 'Playfair Display', serif;
    font-weight: 700;
  }
}

@layer utilities {
  .font-display {
    font-family: 'Playfair Display', serif;
  }
  .font-body {
    font-family: 'Outfit', sans-serif;
  }
  .font-mono {
    font-family: 'JetBrains Mono', monospace;
  }
  .glass {
    background: hsl(var(--card) / 0.6);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid hsl(var(--border) / 0.1);
  }
  .glass-strong {
    background: hsl(var(--card) / 0.8);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border: 1px solid hsl(var(--border) / 0.15);
  }
  .text-gradient {
    background: linear-gradient(135deg, hsl(var(--primary)), hsl(27 96% 70%));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  .glow-primary {
    box-shadow: 0 0 20px hsl(var(--primary) / 0.3), 0 0 40px hsl(var(--primary) / 0.1);
  }
  .glow-primary-sm {
    box-shadow: 0 0 10px hsl(var(--primary) / 0.2);
  }
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes slideInRight {
  from {
    opacity: 0;
    transform: translateX(20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 5px hsl(var(--primary) / 0.3); }
  50% { box-shadow: 0 0 20px hsl(var(--primary) / 0.5); }
}

.animate-shimmer {
  background: linear-gradient(90deg, transparent 0%, hsl(var(--muted) / 0.5) 50%, transparent 100%);
  background-size: 200% 100%;
  animation: shimmer 2s infinite;
}

.animate-fade-in-up {
  animation: fadeInUp 0.5s ease-out forwards;
}

.animate-slide-in-right {
  animation: slideInRight 0.4s ease-out forwards;
}

.animate-pulse-glow {
  animation: pulse-glow 2s ease-in-out infinite;
}
```

- [ ] **Step 2: Update tailwind.config.js**

Replace the entire content of `frontend/tailwind.config.js`:

```js
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      fontFamily: {
        display: ['"Playfair Display"', 'serif'],
        body: ['"Outfit"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        success: {
          DEFAULT: "hsl(var(--success))",
          foreground: "hsl(var(--success-foreground))",
        },
        warning: {
          DEFAULT: "hsl(var(--warning))",
          foreground: "hsl(var(--warning-foreground))",
        },
        info: {
          DEFAULT: "hsl(var(--info))",
          foreground: "hsl(var(--info-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
        xl: "calc(var(--radius) + 4px)",
        "2xl": "calc(var(--radius) + 8px)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: 0 },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: 0 },
        },
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "slide-in-right": {
          "0%": { opacity: "0", transform: "translateX(20px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        "shimmer": {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "pulse-glow": {
          "0%, 100%": { boxShadow: "0 0 5px hsl(var(--primary) / 0.3)" },
          "50%": { boxShadow: "0 0 20px hsl(var(--primary) / 0.5)" },
        },
        "scale-in": {
          "0%": { opacity: "0", transform: "scale(0.95)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "fade-in-up": "fade-in-up 0.5s ease-out forwards",
        "fade-in": "fade-in 0.3s ease-out forwards",
        "slide-in-right": "slide-in-right 0.4s ease-out forwards",
        "shimmer": "shimmer 2s infinite",
        "pulse-glow": "pulse-glow 2s ease-in-out infinite",
        "scale-in": "scale-in 0.3s ease-out forwards",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
```

- [ ] **Step 3: Verify build still works**

Run: `cd /home/jeanfrusca/Projetos/jellyfin_automation/frontend && npm run build`
Expected: Build completes without errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/index.css frontend/tailwind.config.js
git commit -m "feat: add glassmorphism foundation - css vars, fonts, tailwind config"
```

---

### Task 2: Theme Context

**Files:**
- Create: `frontend/src/context/ThemeContext.tsx`

- [ ] **Step 1: Create ThemeContext.tsx**

```tsx
import React, { createContext, useContext, useEffect, useState } from 'react';

type Theme = 'light' | 'dark';

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('theme') as Theme | null;
      if (stored) return stored;
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return 'dark';
  });

  useEffect(() => {
    const root = window.document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setThemeState((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme);
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}
```

- [ ] **Step 2: Update main.tsx to wrap with ThemeProvider**

Replace `frontend/src/main.tsx`:

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { ThemeProvider } from './context/ThemeContext'
import App from './App'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      retry: 1,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  </React.StrictMode>,
)
```

- [ ] **Step 3: Verify build**

Run: `cd /home/jeanfrusca/Projetos/jellyfin_automation/frontend && npm run build`
Expected: Build completes without errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/context/ThemeContext.tsx frontend/src/main.tsx
git commit -m "feat: add ThemeContext with localStorage and prefers-color-scheme"
```

---

### Task 3: ThemeToggle Component

**Files:**
- Create: `frontend/src/components/ThemeToggle.tsx`

- [ ] **Step 1: Create ThemeToggle.tsx**

```tsx
import React from 'react';
import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export const ThemeToggle: React.FC = () => {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className="relative w-10 h-10 rounded-full glass flex items-center justify-center
                 transition-all duration-400 hover:glow-primary-sm hover:scale-105
                 active:scale-95"
      aria-label={theme === 'dark' ? 'Mudar para tema claro' : 'Mudar para tema escuro'}
    >
      <Sun
        className={`w-5 h-5 text-primary absolute transition-all duration-400
                    ${theme === 'dark' ? 'rotate-90 opacity-0 scale-50' : 'rotate-0 opacity-100 scale-100'}`}
      />
      <Moon
        className={`w-5 h-5 text-primary absolute transition-all duration-400
                    ${theme === 'dark' ? 'rotate-0 opacity-100 scale-100' : '-rotate-90 opacity-0 scale-50'}`}
      />
    </button>
  );
};
```

- [ ] **Step 2: Verify build**

Run: `cd /home/jeanfrusca/Projetos/jellyfin_automation/frontend && npm run build`
Expected: Build completes without errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ThemeToggle.tsx
git commit -m "feat: add ThemeToggle component with sun/moon rotation"
```

---

### Task 4: Header Component

**Files:**
- Create: `frontend/src/components/Header.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create Header.tsx**

```tsx
import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Search, Download, Settings, Home, FileText, Play } from 'lucide-react';
import { ThemeToggle } from './ThemeToggle';

const navItems = [
  { path: '/', icon: Home, label: 'Início' },
  { path: '/search', icon: Search, label: 'Buscar' },
  { path: '/downloads', icon: Download, label: 'Downloads' },
  { path: '/settings', icon: Settings, label: 'Configurações' },
  { path: '/logs', icon: FileText, label: 'Logs' },
];

export const Header: React.FC = () => {
  const location = useLocation();

  return (
    <header className="fixed top-0 left-0 right-0 z-50 glass-strong">
      <div className="container mx-auto px-6 lg:px-12">
        <div className="flex items-center justify-between h-[72px]">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3 group">
            <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center
                          shadow-lg shadow-primary/20 group-hover:shadow-primary/40
                          transition-shadow duration-300">
              <Play className="w-5 h-5 text-primary-foreground fill-current" />
            </div>
            <span className="font-display text-xl font-bold text-gradient hidden sm:block">
              Jellyfin Automation
            </span>
          </Link>

          {/* Navigation */}
          <nav className="flex items-center gap-1">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`relative flex items-center gap-2 px-4 py-2 rounded-xl
                            text-sm font-medium font-body transition-all duration-300
                            ${isActive
                              ? 'text-primary bg-primary/10'
                              : 'text-muted-foreground hover:text-foreground hover:bg-accent'
                            }`}
                >
                  <item.icon className={`w-4 h-4 transition-transform duration-300
                                        ${isActive ? '' : 'group-hover:-translate-y-0.5'}`} />
                  <span className="hidden md:inline">{item.label}</span>
                  {isActive && (
                    <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-4 h-0.5
                                   rounded-full bg-primary" />
                  )}
                </Link>
              );
            })}
          </nav>

          {/* Right side */}
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <div className="w-9 h-9 rounded-full bg-primary/10 border border-primary/20
                          flex items-center justify-center">
              <span className="text-sm font-semibold text-primary">JA</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
```

- [ ] **Step 2: Update App.tsx with new layout**

Replace `frontend/src/App.tsx`:

```tsx
import { Routes, Route } from 'react-router-dom';
import { Header } from './components/Header';
import HomePage from './pages/Home';
import SearchPage from './pages/Search';
import DownloadsPage from './pages/Downloads';
import SettingsPage from './pages/Settings';
import LogsPage from './pages/Logs';

function App() {
  return (
    <div className="min-h-screen bg-background font-body">
      <Header />
      <main className="container mx-auto px-6 lg:px-12 pt-24 pb-16">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/downloads" element={<DownloadsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/logs" element={<LogsPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
```

- [ ] **Step 3: Verify build**

Run: `cd /home/jeanfrusca/Projetos/jellyfin_automation/frontend && npm run build`
Expected: Build completes without errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/Header.tsx frontend/src/App.tsx
git commit -m "feat: add glassmorphism Header with nav, logo, and theme toggle"
```

---

### Task 5: Home Page Redesign

**Files:**
- Modify: `frontend/src/pages/Home.tsx`

- [ ] **Step 1: Redesign Home.tsx**

Replace `frontend/src/pages/Home.tsx`:

```tsx
import React from 'react';
import { Link } from 'react-router-dom';
import { Search, Download, Settings, ArrowRight } from 'lucide-react';

const features = [
  {
    title: 'Buscar Conteúdo',
    description: 'Pesquise filmes, séries e animes no TMDB com resultados instantâneos',
    icon: Search,
    link: '/search',
    color: 'from-orange-400/20 to-orange-600/10',
    iconColor: 'text-orange-400',
  },
  {
    title: 'Downloads',
    description: 'Monitore e gerencie seus downloads em tempo real',
    icon: Download,
    link: '/downloads',
    color: 'from-sky-400/20 to-sky-600/10',
    iconColor: 'text-sky-400',
  },
  {
    title: 'Configurações',
    description: 'Configure paths, APIs e preferências do sistema',
    icon: Settings,
    link: '/settings',
    color: 'from-emerald-400/20 to-emerald-600/10',
    iconColor: 'text-emerald-400',
  },
];

const HomePage: React.FC = () => {
  return (
    <div className="space-y-12 animate-fade-in">
      {/* Hero */}
      <section className="text-center space-y-6 py-12">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass
                      text-sm font-medium text-primary mb-4">
          <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
          Sistema ativo e pronto
        </div>
        <h1 className="font-display text-4xl md:text-5xl lg:text-6xl font-bold
                     text-foreground leading-tight">
          Bem-vindo ao{' '}
          <span className="text-gradient">Jellyfin Automation</span>
        </h1>
        <p className="text-muted-foreground text-lg md:text-xl max-w-2xl mx-auto leading-relaxed">
          Automatize a busca, download e organização de conteúdo para seu servidor Jellyfin
          com uma experiência fluida e intuitiva.
        </p>
      </section>

      {/* Features Grid */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {features.map((feature, index) => (
          <Link
            key={feature.title}
            to={feature.link}
            className="group relative"
            style={{ animationDelay: `${index * 100}ms` }}
          >
            <div className="relative h-full glass rounded-2xl p-6
                          transition-all duration-300
                          hover:-translate-y-1 hover:shadow-xl
                          hover:shadow-primary/5 hover:border-primary/20
                          overflow-hidden">
              {/* Background gradient */}
              <div className={`absolute inset-0 bg-gradient-to-br ${feature.color} opacity-0
                            group-hover:opacity-100 transition-opacity duration-500`} />

              <div className="relative z-10 space-y-4">
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${feature.color}
                              flex items-center justify-center
                              group-hover:scale-110 transition-transform duration-300`}>
                  <feature.icon className={`w-6 h-6 ${feature.iconColor}`} />
                </div>
                <div>
                  <h3 className="font-display text-xl font-bold text-foreground mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-muted-foreground text-sm leading-relaxed">
                    {feature.description}
                  </p>
                </div>
                <div className="flex items-center gap-2 text-primary text-sm font-medium
                              opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                  <span>Explorar</span>
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </div>
              </div>
            </div>
          </Link>
        ))}
      </section>

      {/* Stats or decorative section */}
      <section className="glass rounded-2xl p-8 text-center">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="space-y-2">
            <div className="font-display text-3xl font-bold text-gradient">TMDB</div>
            <div className="text-muted-foreground text-sm">Busca de conteúdo</div>
          </div>
          <div className="space-y-2">
            <div className="font-display text-3xl font-bold text-gradient">Jackett</div>
            <div className="text-muted-foreground text-sm">Indexação de torrents</div>
          </div>
          <div className="space-y-2">
            <div className="font-display text-3xl font-bold text-gradient">qBittorrent</div>
            <div className="text-muted-foreground text-sm">Gerenciamento de downloads</div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default HomePage;
```

- [ ] **Step 2: Verify build**

Run: `cd /home/jeanfrusca/Projetos/jellyfin_automation/frontend && npm run build`
Expected: Build completes without errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Home.tsx
git commit -m "feat: redesign Home page with glassmorphism hero and feature cards"
```

---

### Task 6: SearchBar and MediaCard Redesign

**Files:**
- Modify: `frontend/src/components/SearchBar.tsx`
- Modify: `frontend/src/components/MediaCard.tsx`

- [ ] **Step 1: Redesign SearchBar.tsx**

Replace `frontend/src/components/SearchBar.tsx`:

```tsx
import React, { useState } from 'react';
import { Search, Loader2 } from 'lucide-react';

interface SearchBarProps {
  onSearch: (query: string) => void;
  isLoading?: boolean;
}

export const SearchBar: React.FC<SearchBarProps> = ({ onSearch, isLoading }) => {
  const [query, setQuery] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto">
      <div className="relative group">
        <div className="absolute inset-0 rounded-2xl bg-primary/10 blur-xl opacity-0
                      group-focus-within:opacity-100 transition-opacity duration-500" />
        <div className="relative flex items-center glass rounded-2xl
                      focus-within:ring-2 focus-within:ring-primary/30
                      focus-within:border-primary/30
                      transition-all duration-300">
          <Search className="w-5 h-5 text-muted-foreground ml-5" />
          <input
            type="text"
            placeholder="Buscar filmes, séries ou animes..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="flex-1 bg-transparent border-none outline-none
                     px-4 py-4 text-foreground placeholder:text-muted-foreground/60
                     font-body text-base"
          />
          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="mr-2 px-6 py-2.5 rounded-xl bg-primary text-primary-foreground
                     font-medium text-sm
                     hover:bg-primary/90 hover:shadow-lg hover:shadow-primary/20
                     active:scale-[0.98]
                     disabled:opacity-50 disabled:cursor-not-allowed
                     transition-all duration-200 flex items-center gap-2"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Buscando</span>
              </>
            ) : (
              <span>Buscar</span>
            )}
          </button>
        </div>
      </div>
    </form>
  );
};
```

- [ ] **Step 2: Redesign MediaCard.tsx**

Replace `frontend/src/components/MediaCard.tsx`:

```tsx
import React from 'react';
import { Play, Star } from 'lucide-react';
import { TMDBSearchResult } from '../types';

interface MediaCardProps {
  media: TMDBSearchResult;
  onClick: (media: TMDBSearchResult) => void;
}

export const MediaCard: React.FC<MediaCardProps> = ({ media, onClick }) => {
  const title = media.title || media.name || 'Unknown';
  const year = media.release_date
    ? new Date(media.release_date).getFullYear()
    : media.first_air_date
    ? new Date(media.first_air_date).getFullYear()
    : null;

  return (
    <div
      className="group relative cursor-pointer rounded-xl overflow-hidden
                transition-all duration-300 hover:-translate-y-2
                hover:shadow-2xl hover:shadow-primary/10"
      onClick={() => onClick(media)}
    >
      {/* Poster */}
      <div className="aspect-[2/3] relative bg-muted overflow-hidden">
        {media.poster_path ? (
          <img
            src={`https://image.tmdb.org/t/p/w500${media.poster_path}`}
            alt={title}
            className="w-full h-full object-cover
                     group-hover:scale-105 transition-transform duration-500"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-muted">
            <span className="text-muted-foreground text-sm">Sem imagem</span>
          </div>
        )}

        {/* Hover overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/40 to-transparent
                      opacity-0 group-hover:opacity-100 transition-opacity duration-300
                      flex flex-col justify-end p-4">
          <div className="transform translate-y-4 group-hover:translate-y-0 transition-transform duration-300">
            <div className="w-12 h-12 rounded-full bg-primary/90 flex items-center justify-center
                          mx-auto mb-3 shadow-lg shadow-primary/30">
              <Play className="w-5 h-5 text-white fill-current ml-0.5" />
            </div>
            <p className="text-white text-xs text-center font-medium line-clamp-2">
              Ver torrents disponíveis
            </p>
          </div>
        </div>

        {/* Type badge */}
        <div className="absolute top-3 left-3">
          <span className={`px-2.5 py-1 rounded-lg text-xs font-semibold uppercase tracking-wider
                         ${media.media_type === 'movie'
                           ? 'bg-primary/90 text-primary-foreground'
                           : 'bg-sky-500/90 text-white'
                         }`}>
            {media.media_type === 'movie' ? 'Filme' : 'Série'}
          </span>
        </div>
      </div>

      {/* Info */}
      <div className="p-3 bg-card/80 backdrop-blur-sm">
        <h3 className="font-body font-semibold text-sm text-foreground line-clamp-1 mb-1">
          {title}
        </h3>
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          {year && <span>{year}</span>}
          {media.vote_average > 0 && (
            <div className="flex items-center gap-1">
              <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" />
              <span className="font-medium">{media.vote_average.toFixed(1)}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
```

- [ ] **Step 3: Verify build**

Run: `cd /home/jeanfrusca/Projetos/jellyfin_automation/frontend && npm run build`
Expected: Build completes without errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/SearchBar.tsx frontend/src/components/MediaCard.tsx
git commit -m "feat: redesign SearchBar and MediaCard with glassmorphism effects"
```

---

### Task 7: Search Page Redesign

**Files:**
- Modify: `frontend/src/pages/Search.tsx`

- [ ] **Step 1: Redesign Search.tsx**

Replace `frontend/src/pages/Search.tsx`:

```tsx
import React, { useState } from 'react';
import { useQuery, skipToken } from '@tanstack/react-query';
import { SearchBar } from '../components/SearchBar';
import { MediaCard } from '../components/MediaCard';
import { TorrentList } from '../components/TorrentList';
import { searchAPI, downloadAPI } from '../services/api';
import { TMDBSearchResult, TorrentResult } from '../types';

const SearchPage: React.FC = () => {
  const [selectedMedia, setSelectedMedia] = useState<TMDBSearchResult | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const { data: searchResults, isLoading: isSearching } = useQuery({
    queryKey: ['search', searchQuery],
    queryFn: () => searchAPI.searchMedia(searchQuery),
    enabled: !!searchQuery,
  });

  const { data: torrentResults } = useQuery({
    queryKey: ['torrents', selectedMedia?.id],
    queryFn: selectedMedia
      ? () =>
          searchAPI.searchTorrents({
            tmdb_id: selectedMedia.id,
            title: selectedMedia.title || selectedMedia.name || '',
            type: selectedMedia.media_type,
          })
      : skipToken,
  });

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    setSelectedMedia(null);
  };

  const handleMediaClick = (media: TMDBSearchResult) => {
    setSelectedMedia(media);
  };

  const handleDownload = async (torrent: TorrentResult) => {
    if (!selectedMedia) return;
    try {
      await downloadAPI.createDownload({
        tmdb_id: selectedMedia.id,
        title: selectedMedia.title || selectedMedia.name || '',
        type: selectedMedia.media_type,
        torrent_name: torrent.title,
        magnet_link: torrent.magnet_url || torrent.download_url || '',
        quality: torrent.quality || '1080p',
        language_preference: torrent.language || 'legendado',
        indexer_used: torrent.indexer,
      });
      alert('Download iniciado com sucesso!');
    } catch (error) {
      console.error('Failed to start download:', error);
      alert('Erro ao iniciar download.');
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="text-center space-y-4">
        <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground">
          Buscar Conteúdo
        </h2>
        <p className="text-muted-foreground max-w-xl mx-auto">
          Pesquise por filmes, séries ou animes no banco de dados do TMDB
        </p>
      </div>

      {/* Search */}
      <SearchBar onSearch={handleSearch} isLoading={isSearching} />

      {/* Results */}
      {searchResults?.data?.results && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-display text-xl font-bold text-foreground">
              Resultados
            </h3>
            <span className="text-sm text-muted-foreground">
              {searchResults.data.results.length} encontrados
            </span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {searchResults.data.results.map((media: TMDBSearchResult) => (
              <MediaCard
                key={media.id}
                media={media}
                onClick={handleMediaClick}
              />
            ))}
          </div>
        </div>
      )}

      {/* Torrents */}
      {selectedMedia && (
        <div className="space-y-4 animate-fade-in-up">
          <div className="glass rounded-2xl p-6">
            <h3 className="font-display text-xl font-bold text-foreground mb-1">
              Torrents para: {selectedMedia.title || selectedMedia.name}
            </h3>
            <p className="text-muted-foreground text-sm mb-4">
              Selecione um torrent para iniciar o download
            </p>
            <TorrentList
              torrents={torrentResults?.data || []}
              onDownload={handleDownload}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default SearchPage;
```

- [ ] **Step 2: Verify build**

Run: `cd /home/jeanfrusca/Projetos/jellyfin_automation/frontend && npm run build`
Expected: Build completes without errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Search.tsx
git commit -m "feat: redesign Search page with glassmorphism layout"
```

---

### Task 8: TorrentList Redesign

**Files:**
- Modify: `frontend/src/components/TorrentList.tsx`

- [ ] **Step 1: Redesign TorrentList.tsx**

Replace `frontend/src/components/TorrentList.tsx`:

```tsx
import React from 'react';
import { Download, ArrowUpCircle, ArrowDownCircle } from 'lucide-react';
import { TorrentResult } from '../types';

interface TorrentListProps {
  torrents: TorrentResult[];
  onDownload: (torrent: TorrentResult) => void;
}

export const TorrentList: React.FC<TorrentListProps> = ({ torrents, onDownload }) => {
  if (torrents.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mx-auto mb-4">
          <Download className="w-8 h-8 text-muted-foreground/50" />
        </div>
        <p className="text-lg font-medium">Nenhum torrent encontrado</p>
        <p className="text-sm mt-1">Tente buscar com termos diferentes</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {torrents.map((torrent, index) => (
        <div
          key={index}
          className="group flex items-center gap-4 p-4 rounded-xl
                    glass hover:border-primary/20
                    transition-all duration-300 hover:-translate-y-0.5"
          style={{ animationDelay: `${index * 50}ms` }}
        >
          <div className="flex-1 min-w-0">
            <h4 className="font-body font-semibold text-foreground truncate mb-2">
              {torrent.title}
            </h4>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted-foreground">
              <span className="font-mono text-xs">{torrent.indexer}</span>
              <span className="w-1 h-1 rounded-full bg-muted-foreground/40" />
              <span className="font-mono text-xs">{torrent.size}</span>
              <span className="w-1 h-1 rounded-full bg-muted-foreground/40" />
              <div className="flex items-center gap-1 text-emerald-500">
                <ArrowUpCircle className="w-3.5 h-3.5" />
                <span className="font-mono font-medium">{torrent.seeds}</span>
              </div>
              <div className="flex items-center gap-1 text-sky-500">
                <ArrowDownCircle className="w-3.5 h-3.5" />
                <span className="font-mono font-medium">{torrent.peers}</span>
              </div>
            </div>
            <div className="flex flex-wrap gap-2 mt-3">
              {torrent.quality && (
                <span className="px-2.5 py-1 rounded-lg text-xs font-semibold uppercase tracking-wider
                              bg-primary/10 text-primary border border-primary/20">
                  {torrent.quality}
                </span>
              )}
              {torrent.language && (
                <span className="px-2.5 py-1 rounded-lg text-xs font-semibold uppercase tracking-wider
                              bg-muted text-muted-foreground border border-border">
                  {torrent.language}
                </span>
              )}
              {torrent.release_group && (
                <span className="px-2.5 py-1 rounded-lg text-xs font-semibold uppercase tracking-wider
                              bg-muted text-muted-foreground border border-border">
                  {torrent.release_group}
                </span>
              )}
            </div>
          </div>
          <button
            onClick={() => onDownload(torrent)}
            className="flex-shrink-0 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground
                     font-medium text-sm
                     hover:bg-primary/90 hover:shadow-lg hover:shadow-primary/20
                     active:scale-[0.98]
                     transition-all duration-200 flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            <span className="hidden sm:inline">Baixar</span>
          </button>
        </div>
      ))}
    </div>
  );
};
```

- [ ] **Step 2: Verify build**

Run: `cd /home/jeanfrusca/Projetos/jellyfin_automation/frontend && npm run build`
Expected: Build completes without errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/TorrentList.tsx
git commit -m "feat: redesign TorrentList with glass items and metadata badges"
```

---

### Task 9: DownloadMonitor Redesign

**Files:**
- Modify: `frontend/src/components/DownloadMonitor.tsx`

- [ ] **Step 1: Redesign DownloadMonitor.tsx**

Replace `frontend/src/components/DownloadMonitor.tsx`:

```tsx
import React from 'react';
import { Pause, Play, Trash2, Download, CheckCircle2, AlertCircle, Clock } from 'lucide-react';
import { Download as DownloadType } from '../types';

interface DownloadMonitorProps {
  downloads: DownloadType[];
  onPause: (id: number) => void;
  onResume: (id: number) => void;
  onCancel: (id: number) => void;
}

const statusConfig: Record<string, { icon: React.ElementType; color: string; bg: string; label: string }> = {
  downloading: { icon: Download, color: 'text-sky-400', bg: 'bg-sky-400/10', label: 'Baixando' },
  completed: { icon: CheckCircle2, color: 'text-emerald-400', bg: 'bg-emerald-400/10', label: 'Concluído' },
  failed: { icon: AlertCircle, color: 'text-red-400', bg: 'bg-red-400/10', label: 'Falhou' },
  cancelled: { icon: Trash2, color: 'text-muted-foreground', bg: 'bg-muted', label: 'Cancelado' },
  paused: { icon: Pause, color: 'text-amber-400', bg: 'bg-amber-400/10', label: 'Pausado' },
  queued: { icon: Clock, color: 'text-purple-400', bg: 'bg-purple-400/10', label: 'Na fila' },
};

export const DownloadMonitor: React.FC<DownloadMonitorProps> = ({
  downloads,
  onPause,
  onResume,
  onCancel,
}) => {
  if (downloads.length === 0) {
    return (
      <div className="text-center py-16 text-muted-foreground">
        <div className="w-20 h-20 rounded-full bg-muted flex items-center justify-center mx-auto mb-6">
          <Download className="w-10 h-10 text-muted-foreground/40" />
        </div>
        <p className="text-xl font-display font-bold mb-2">Nenhum download ativo</p>
        <p className="text-sm">Vá para a página de busca para adicionar downloads</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {downloads.map((download, index) => {
        const status = statusConfig[download.status] || statusConfig.queued;
        const StatusIcon = status.icon;
        const progress = Math.round(download.progress * 100);

        return (
          <div
            key={download.id}
            className="glass rounded-2xl p-5 transition-all duration-300
                     hover:border-primary/20 hover:-translate-y-0.5"
            style={{ animationDelay: `${index * 50}ms` }}
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3 min-w-0">
                <div className={`w-10 h-10 rounded-xl ${status.bg} flex items-center justify-center flex-shrink-0`}>
                  <StatusIcon className={`w-5 h-5 ${status.color}`} />
                </div>
                <div className="min-w-0">
                  <h4 className="font-body font-semibold text-foreground truncate">
                    {download.title}
                  </h4>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className={`text-xs font-semibold uppercase tracking-wider px-2 py-0.5 rounded-md ${status.bg} ${status.color}`}>
                      {status.label}
                    </span>
                    <span className="text-xs text-muted-foreground font-mono">
                      {download.quality || '1080p'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 flex-shrink-0">
                {download.status === 'downloading' && (
                  <button
                    onClick={() => onPause(download.id)}
                    className="w-9 h-9 rounded-lg glass flex items-center justify-center
                             hover:bg-amber-400/10 hover:text-amber-400
                             active:scale-95 transition-all duration-200"
                    title="Pausar"
                  >
                    <Pause className="w-4 h-4" />
                  </button>
                )}
                {download.status === 'paused' && (
                  <button
                    onClick={() => onResume(download.id)}
                    className="w-9 h-9 rounded-lg glass flex items-center justify-center
                             hover:bg-emerald-400/10 hover:text-emerald-400
                             active:scale-95 transition-all duration-200"
                    title="Retomar"
                  >
                    <Play className="w-4 h-4" />
                  </button>
                )}
                <button
                  onClick={() => onCancel(download.id)}
                  className="w-9 h-9 rounded-lg glass flex items-center justify-center
                           hover:bg-red-400/10 hover:text-red-400
                           active:scale-95 transition-all duration-200"
                  title="Cancelar"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Progress */}
            {download.status === 'downloading' && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-mono font-semibold text-primary">{progress}%</span>
                  <div className="flex items-center gap-4 text-muted-foreground text-xs font-mono">
                    {download.speed && <span>{download.speed}</span>}
                    {download.eta && <span>ETA: {download.eta}</span>}
                  </div>
                </div>
                <div className="h-2 rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-primary to-orange-300
                             transition-all duration-500 ease-out relative"
                    style={{ width: `${progress}%` }}
                  >
                    {progress < 100 && (
                      <div className="absolute inset-0 animate-shimmer" />
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
```

- [ ] **Step 2: Verify build**

Run: `cd /home/jeanfrusca/Projetos/jellyfin_automation/frontend && npm run build`
Expected: Build completes without errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/DownloadMonitor.tsx
git commit -m "feat: redesign DownloadMonitor with glass cards and animated progress"
```

---

### Task 10: Downloads Page Redesign

**Files:**
- Modify: `frontend/src/pages/Downloads.tsx`

- [ ] **Step 1: Redesign Downloads.tsx**

Replace `frontend/src/pages/Downloads.tsx`:

```tsx
import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { DownloadMonitor } from '../components/DownloadMonitor';
import { downloadAPI } from '../services/api';

const DownloadsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { data: downloads, isLoading } = useQuery({
    queryKey: ['downloads'],
    queryFn: () => downloadAPI.listDownloads(),
    refetchInterval: 5000,
  });

  const pauseMutation = useMutation({
    mutationFn: (id: number) => downloadAPI.pauseDownload(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['downloads'] }),
  });

  const resumeMutation = useMutation({
    mutationFn: (id: number) => downloadAPI.resumeDownload(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['downloads'] }),
  });

  const cancelMutation = useMutation({
    mutationFn: (id: number) => downloadAPI.cancelDownload(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['downloads'] }),
  });

  const handlePause = (id: number) => pauseMutation.mutate(id);
  const handleResume = (id: number) => resumeMutation.mutate(id);
  const handleCancel = (id: number) => {
    if (window.confirm('Tem certeza que deseja cancelar este download?')) {
      cancelMutation.mutate(id);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-8 animate-fade-in">
        <div className="text-center space-y-4">
          <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground">
            Downloads
          </h2>
          <p className="text-muted-foreground">Gerencie seus downloads ativos</p>
        </div>
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="glass rounded-2xl p-5 h-32 animate-shimmer" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="text-center space-y-4">
        <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground">
          Downloads
        </h2>
        <p className="text-muted-foreground max-w-xl mx-auto">
          Monitore e gerencie todos os seus downloads em tempo real
        </p>
      </div>

      <DownloadMonitor
        downloads={downloads?.data || []}
        onPause={handlePause}
        onResume={handleResume}
        onCancel={handleCancel}
      />
    </div>
  );
};

export default DownloadsPage;
```

- [ ] **Step 2: Verify build**

Run: `cd /home/jeanfrusca/Projetos/jellyfin_automation/frontend && npm run build`
Expected: Build completes without errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Downloads.tsx
git commit -m "feat: redesign Downloads page with loading skeletons"
```

---

### Task 11: Settings Page Redesign

**Files:**
- Modify: `frontend/src/pages/Settings.tsx`

- [ ] **Step 1: Redesign Settings.tsx**

Replace `frontend/src/pages/Settings.tsx`:

```tsx
import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Folder, Film, Tv, Sparkles, Languages, Save } from 'lucide-react';
import { settingsAPI } from '../services/api';

const settingGroups = [
  {
    icon: Folder,
    title: 'Caminhos',
    description: 'Diretórios onde o conteúdo será salvo',
    settings: [
      { key: 'movies_path', label: 'Pasta de Filmes', placeholder: '/media/movies' },
      { key: 'series_path', label: 'Pasta de Séries', placeholder: '/media/series' },
      { key: 'animes_path', label: 'Pasta de Animes', placeholder: '/media/animes' },
    ],
  },
  {
    icon: Sparkles,
    title: 'Preferências',
    description: 'Configurações padrão para novos downloads',
    settings: [
      { key: 'default_quality', label: 'Qualidade Padrão', placeholder: '1080p' },
      { key: 'default_language', label: 'Idioma Padrão', placeholder: 'legendado' },
    ],
  },
];

const SettingsPage: React.FC = () => {
  const queryClient = useQueryClient();

  const { data: currentSettings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: () => settingsAPI.getSettings(),
  });

  const updateMutation = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      settingsAPI.updateSetting(key, value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    },
  });

  const handleUpdate = (key: string, value: string) => {
    if (value) {
      updateMutation.mutate({ key, value });
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-8 animate-fade-in">
        <div className="text-center space-y-4">
          <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground">
            Configurações
          </h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[1, 2].map((i) => (
            <div key={i} className="glass rounded-2xl p-6 h-64 animate-shimmer" />
          ))}
        </div>
      </div>
    );
  }

  const currentValues = currentSettings?.data || {};

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="text-center space-y-4">
        <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground">
          Configurações
        </h2>
        <p className="text-muted-foreground max-w-xl mx-auto">
          Configure os caminhos de mídia e preferências de download
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {settingGroups.map((group) => (
          <div
            key={group.title}
            className="glass rounded-2xl p-6 space-y-6
                     transition-all duration-300 hover:border-primary/20"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                <group.icon className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h3 className="font-display text-lg font-bold text-foreground">
                  {group.title}
                </h3>
                <p className="text-sm text-muted-foreground">{group.description}</p>
              </div>
            </div>

            <div className="space-y-4">
              {group.settings.map((setting) => (
                <div key={setting.key} className="space-y-2">
                  <label className="text-sm font-medium text-foreground">
                    {setting.label}
                  </label>
                  <div className="relative group">
                    <input
                      type="text"
                      defaultValue={currentValues[setting.key] || ''}
                      placeholder={setting.placeholder}
                      onBlur={(e) => handleUpdate(setting.key, e.target.value)}
                      className="w-full px-4 py-3 rounded-xl glass bg-transparent
                               border border-border/50
                               focus:outline-none focus:ring-2 focus:ring-primary/30
                               focus:border-primary/30
                               text-foreground placeholder:text-muted-foreground/50
                               font-mono text-sm
                               transition-all duration-200"
                    />
                    {updateMutation.isPending && updateMutation.variables?.key === setting.key && (
                      <Save className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-primary animate-pulse" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SettingsPage;
```

- [ ] **Step 2: Verify build**

Run: `cd /home/jeanfrusca/Projetos/jellyfin_automation/frontend && npm run build`
Expected: Build completes without errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Settings.tsx
git commit -m "feat: redesign Settings page with grouped glass config cards"
```

---

### Task 12: Logs Page Redesign

**Files:**
- Modify: `frontend/src/pages/Logs.tsx`

- [ ] **Step 1: Redesign Logs.tsx**

Replace `frontend/src/pages/Logs.tsx`:

```tsx
import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, FileText, AlertTriangle, Info, Bug, XCircle } from 'lucide-react';
import { logsAPI } from '../services/api';

const levelOptions = [
  { value: '', label: 'Todos', icon: FileText },
  { value: 'DEBUG', label: 'DEBUG', icon: Bug, color: 'text-muted-foreground' },
  { value: 'INFO', label: 'INFO', icon: Info, color: 'text-sky-400' },
  { value: 'WARNING', label: 'WARNING', icon: AlertTriangle, color: 'text-amber-400' },
  { value: 'ERROR', label: 'ERROR', icon: XCircle, color: 'text-red-400' },
];

const LogsPage: React.FC = () => {
  const [search, setSearch] = useState('');
  const [level, setLevel] = useState('');

  const { data: logs, isLoading } = useQuery({
    queryKey: ['logs', level, search],
    queryFn: () => logsAPI.getLogs({ level, search }),
  });

  if (isLoading) {
    return (
      <div className="space-y-8 animate-fade-in">
        <div className="text-center space-y-4">
          <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground">Logs</h2>
        </div>
        <div className="glass rounded-2xl p-4 h-[600px] animate-shimmer" />
      </div>
    );
  }

  const logLines = logs?.data?.logs || [];

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="text-center space-y-4">
        <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground">
          Logs
        </h2>
        <p className="text-muted-foreground max-w-xl mx-auto">
          Visualize e filtre os logs do sistema
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1 group">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Filtrar logs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-11 pr-4 py-3 rounded-xl glass bg-transparent
                     border border-border/50
                     focus:outline-none focus:ring-2 focus:ring-primary/30
                     focus:border-primary/30
                     text-foreground placeholder:text-muted-foreground/50
                     text-sm transition-all duration-200"
          />
        </div>
        <div className="flex gap-2">
          {levelOptions.map((opt) => {
            const Icon = opt.icon;
            const isActive = level === opt.value;
            return (
              <button
                key={opt.value}
                onClick={() => setLevel(opt.value)}
                className={`px-3 py-2 rounded-xl text-xs font-semibold uppercase tracking-wider
                          flex items-center gap-1.5 transition-all duration-200
                          ${isActive
                            ? 'bg-primary text-primary-foreground shadow-lg shadow-primary/20'
                            : 'glass text-muted-foreground hover:text-foreground hover:bg-accent'
                          }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">{opt.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Log Terminal */}
      <div className="glass rounded-2xl p-1 overflow-hidden">
        <div className="rounded-xl bg-black/90 dark:bg-black/90 bg-stone-900/95
                      p-4 font-mono text-sm h-[600px] overflow-auto">
          {logLines.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
              <FileText className="w-12 h-12 mb-4 opacity-30" />
              <p>Nenhum log encontrado</p>
            </div>
          ) : (
            <div className="space-y-1">
              {logLines.map((line: string, index: number) => (
                <div
                  key={index}
                  className="py-1 px-2 rounded hover:bg-white/5 transition-colors
                           text-stone-300 leading-relaxed break-all"
                >
                  {line}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default LogsPage;
```

- [ ] **Step 2: Verify build**

Run: `cd /home/jeanfrusca/Projetos/jellyfin_automation/frontend && npm run build`
Expected: Build completes without errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Logs.tsx
git commit -m "feat: redesign Logs page with terminal styling and filter pills"
```

---

### Task 13: Final Verification

**Files:**
- All frontend files

- [ ] **Step 1: Run full build**

Run: `cd /home/jeanfrusca/Projetos/jellyfin_automation/frontend && npm run build`
Expected: Build completes with zero errors

- [ ] **Step 2: Run linter**

Run: `cd /home/jeanfrusca/Projetos/jellyfin_automation/frontend && npm run lint`
Expected: No critical lint errors (warnings acceptable)

- [ ] **Step 3: Commit final changes**

```bash
git add frontend/
git commit -m "feat: complete glassmorphism premium UI redesign with light/dark theme"
```

---

## Self-Review Checklist

### 1. Spec Coverage
- [x] CSS variables for light/dark themes
- [x] Google Fonts (Playfair Display, Outfit, JetBrains Mono)
- [x] Glassmorphism utility classes
- [x] ThemeContext with localStorage + prefers-color-scheme
- [x] ThemeToggle with sun/moon rotation
- [x] Floating glass Header with nav links
- [x] Home page hero + feature cards
- [x] SearchBar with glass effect and focus glow
- [x] MediaCard with hover zoom and overlay
- [x] Search page layout
- [x] TorrentList with glass items
- [x] DownloadMonitor with progress shimmer
- [x] Downloads page with skeletons
- [x] Settings page with grouped cards
- [x] Logs page with terminal styling

### 2. Placeholder Scan
- [x] No TBD/TODO/fill-in-details
- [x] All code blocks contain complete, runnable code
- [x] All file paths are exact
- [x] All commands have expected output

### 3. Type Consistency
- [x] `ThemeContext` uses `Theme` type consistently
- [x] `useTheme` hook returns consistent shape
- [x] Component props match existing types in `frontend/src/types/index.ts`
- [x] All `React.FC` usage consistent

### 4. Dependencies
- [x] No new npm packages needed (uses existing: Tailwind, lucide-react, shadcn/ui)
- [x] Google Fonts loaded via CSS `@import`
- [x] `tailwindcss-animate` already installed
