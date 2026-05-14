# Mobile Responsiveness Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix mobile layout issues on Samsung S23 (360px viewport) across Header, Detail, Downloads, Search, and Settings pages.

**Architecture:** Hybrid approach — targeted responsive fixes using Tailwind breakpoints (`sm`, `md`), a mobile hamburger navigation drawer (shadcn Sheet), and a synopsis expand/collapse feature. All changes are CSS/class-level; no backend modifications needed.

**Tech Stack:** React 18, Tailwind CSS, shadcn/ui, Radix UI, Lucide icons

---

### Task 1: Create Sheet Component for Mobile Navigation Drawer

**Files:**
- Create: `frontend/src/components/ui/sheet.tsx`

The Sheet component uses the same Radix Dialog primitive already installed (`@radix-ui/react-dialog`). It renders a slide-in panel from the side, perfect for mobile navigation.

- [ ] **Step 1: Create sheet.tsx**

```typescript
import * as React from "react"
import * as DialogPrimitive from "@radix-ui/react-dialog"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"

const Sheet = DialogPrimitive.Root
const SheetTrigger = DialogPrimitive.Trigger
const SheetClose = DialogPrimitive.Close
const SheetPortal = DialogPrimitive.Portal

const SheetOverlay = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Overlay>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Overlay
    ref={ref}
    className={cn(
      "fixed inset-0 z-50 bg-black/80 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
      className
    )}
    {...props}
  />
))
SheetOverlay.displayName = "SheetOverlay"

const SheetContent = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>
>(({ className, children, ...props }, ref) => (
  <SheetPortal>
    <SheetOverlay />
    <DialogPrimitive.Content
      ref={ref}
      className={cn(
        "fixed z-50 gap-4 bg-background p-6 shadow-lg transition ease-in-out data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:duration-300 data-[state=open]:duration-500",
        "inset-y-0 right-0 h-full w-3/4 border-l data-[state=closed]:slide-out-to-right data-[state=open]:slide-in-from-right sm:max-w-sm",
        className
      )}
      {...props}
    >
      {children}
      <DialogPrimitive.Close className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-secondary">
        <X className="h-4 w-4" />
        <span className="sr-only">Close</span>
      </DialogPrimitive.Close>
    </DialogPrimitive.Content>
  </SheetPortal>
))
SheetContent.displayName = "SheetContent"

const SheetHeader = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn("flex flex-col space-y-2 text-center sm:text-left", className)}
    {...props}
  />
)
SheetHeader.displayName = "SheetHeader"

const SheetFooter = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn("flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2", className)}
    {...props}
  />
)
SheetFooter.displayName = "SheetFooter"

const SheetTitle = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Title>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Title
    ref={ref}
    className={cn("text-lg font-semibold text-foreground", className)}
    {...props}
  />
))
SheetTitle.displayName = "SheetTitle"

const SheetDescription = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Description
    ref={ref}
    className={cn("text-sm text-muted-foreground", className)}
    {...props}
  />
))
SheetDescription.displayName = "SheetDescription"

export {
  Sheet,
  SheetPortal,
  SheetOverlay,
  SheetTrigger,
  SheetClose,
  SheetContent,
  SheetHeader,
  SheetFooter,
  SheetTitle,
  SheetDescription,
}
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: PASS with no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ui/sheet.tsx
git commit -m "feat: add sheet component for mobile navigation drawer"
```

---

### Task 2: Refactor Header with Mobile Hamburger Menu

**Files:**
- Modify: `frontend/src/components/Header.tsx`

**Goal:** On mobile (<768px), show logo icon + app title + hamburger button. All nav links, theme toggle, and avatar go inside a Sheet drawer. On desktop, keep current layout.

- [ ] **Step 1: Rewrite Header.tsx**

Replace the entire `Header.tsx` with:

```tsx
import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Search, Download, Settings, Home, FileText, Play, Compass, Menu, Moon, Sun } from 'lucide-react';
import { ThemeToggle } from './ThemeToggle';
import {
  Sheet,
  SheetContent,
  SheetTrigger,
} from '@/components/ui/sheet';

const navItems = [
  { path: '/', icon: Home, label: 'Início' },
  { path: '/discover', icon: Compass, label: 'Explorar' },
  { path: '/search', icon: Search, label: 'Buscar' },
  { path: '/downloads', icon: Download, label: 'Downloads' },
  { path: '/settings', icon: Settings, label: 'Configurações' },
  { path: '/logs', icon: FileText, label: 'Logs' },
];

export const Header: React.FC = () => {
  const location = useLocation();
  const [open, setOpen] = useState(false);

  return (
    <header className="fixed top-0 left-0 right-0 z-50 glass-strong">
      <div className="container mx-auto px-4 sm:px-6 lg:px-12">
        <div className="flex items-center justify-between h-[72px]">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3 group">
            <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center
                          shadow-lg shadow-primary/20 group-hover:shadow-primary/40
                          transition-shadow duration-300">
              <Play className="w-5 h-5 text-primary-foreground fill-current" />
            </div>
            <span className="font-display text-xl font-bold text-gradient">
              Jellyfin Automation
            </span>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1">
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
                  <span>{item.label}</span>
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
            {/* Desktop: theme toggle + avatar */}
            <div className="hidden md:flex items-center gap-3">
              <ThemeToggle />
              <div className="w-9 h-9 rounded-full bg-primary/10 border border-primary/20
                            flex items-center justify-center">
                <span className="text-sm font-semibold text-primary">JA</span>
              </div>
            </div>

            {/* Mobile: hamburger menu */}
            <Sheet open={open} onOpenChange={setOpen}>
              <SheetTrigger asChild>
                <button className="md:hidden w-9 h-9 rounded-xl glass flex items-center justify-center
                                 text-muted-foreground hover:text-foreground transition-colors">
                  <Menu className="w-5 h-5" />
                </button>
              </SheetTrigger>
              <SheetContent className="glass-strong">
                <div className="flex flex-col h-full">
                  <div className="flex items-center gap-3 mb-8 pt-2">
                    <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center">
                      <Play className="w-5 h-5 text-primary-foreground fill-current" />
                    </div>
                    <span className="font-display text-xl font-bold text-gradient">
                      Jellyfin Automation
                    </span>
                  </div>

                  <nav className="flex flex-col gap-1 flex-1">
                    {navItems.map((item) => {
                      const isActive = location.pathname === item.path;
                      return (
                        <Link
                          key={item.path}
                          to={item.path}
                          onClick={() => setOpen(false)}
                          className={`flex items-center gap-3 px-4 py-3 rounded-xl
                                    text-base font-medium font-body transition-all duration-300
                                    ${isActive
                                      ? 'text-primary bg-primary/10'
                                      : 'text-muted-foreground hover:text-foreground hover:bg-accent'
                                    }`}
                        >
                          <item.icon className="w-5 h-5" />
                          <span>{item.label}</span>
                        </Link>
                      );
                    })}
                  </nav>

                  <div className="border-t border-border/30 pt-4 mt-4 space-y-4">
                    <div className="flex items-center justify-between px-4 py-2">
                      <span className="text-sm text-muted-foreground">Tema</span>
                      <ThemeToggle />
                    </div>
                    <div className="flex items-center gap-3 px-4 py-2">
                      <div className="w-9 h-9 rounded-full bg-primary/10 border border-primary/20
                                    flex items-center justify-center">
                        <span className="text-sm font-semibold text-primary">JA</span>
                      </div>
                      <span className="text-sm font-medium text-foreground">Jellyfin Admin</span>
                    </div>
                  </div>
                </div>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </div>
    </header>
  );
};
```

Key changes:
- Removed `hidden sm:block` from logo text — now always visible
- Desktop nav wrapped in `hidden md:flex`
- Desktop theme toggle + avatar wrapped in `hidden md:flex`
- Added mobile hamburger button (`md:hidden`) that opens a Sheet
- Sheet contains: logo header, all nav links (with larger tap targets), theme toggle, avatar
- Container padding changed from `px-6 lg:px-12` to `px-4 sm:px-6 lg:px-12`

- [ ] **Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: PASS with no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Header.tsx
git commit -m "feat: add mobile hamburger menu with Sheet drawer to Header"
```

---

### Task 3: Update App.tsx Container Padding for Mobile

**Files:**
- Modify: `frontend/src/App.tsx`

**Goal:** Reduce excessive padding on small screens.

- [ ] **Step 1: Update main container padding**

Change the `<main>` element from:
```tsx
<main className="container mx-auto px-6 lg:px-12 pt-24 pb-16">
```
To:
```tsx
<main className="container mx-auto px-4 sm:px-6 lg:px-12 pt-20 sm:pt-24 pb-16">
```

Full file after change:

```tsx
import { Routes, Route } from 'react-router-dom';
import { Header } from './components/Header';
import HomePage from './pages/Home';
import SearchPage from './pages/Search';
import DetailPage from './pages/Detail';
import DownloadsPage from './pages/Downloads';
import SettingsPage from './pages/Settings';
import LogsPage from './pages/Logs';
import DiscoverPage from './pages/Discover';

function App() {
  return (
    <div className="min-h-screen bg-background font-body">
      <Header />
      <main className="container mx-auto px-4 sm:px-6 lg:px-12 pt-20 sm:pt-24 pb-16">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/discover" element={<DiscoverPage />} />
          <Route path="/detail/:mediaType/:id" element={<DetailPage />} />
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

- [ ] **Step 2: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "fix: reduce container padding on mobile screens"
```

---

### Task 4: Detail Page — Synopsis Expand, Torrent Names, Season Selector

**Files:**
- Modify: `frontend/src/pages/Detail.tsx`

**Goal:** Add "Ler mais" toggle for synopsis, fix torrent name overflow, stack season selectors on mobile.

- [ ] **Step 1: Add synopsisExpanded state and update synopsis display**

Add a new state variable near the other useState calls:
```tsx
const [synopsisExpanded, setSynopsisExpanded] = useState(false);
```

Find the synopsis paragraph in the hero section (around line 194):
```tsx
<p className="text-sm text-muted-foreground mt-2 line-clamp-3">
  {media.overview}
</p>
```

Replace it with:
```tsx
<div>
  <p className={`text-sm text-muted-foreground mt-2 ${synopsisExpanded ? '' : 'line-clamp-3'}`}>
    {media.overview}
  </p>
  {media.overview && media.overview.length > 150 && (
    <button
      onClick={() => setSynopsisExpanded(!synopsisExpanded)}
      className="text-xs text-primary mt-1 hover:underline font-medium"
    >
      {synopsisExpanded ? 'Ler menos' : 'Ler mais'}
    </button>
  )}
</div>
```

- [ ] **Step 2: Fix torrent name overflow in the torrent list**

Find the torrent title in the torrent list section (around line 441):
```tsx
<p className="font-medium text-foreground truncate">{torrent.title}</p>
```

Replace with:
```tsx
<p className="font-medium text-foreground break-all sm:truncate" title={torrent.title}>
  {torrent.title}
</p>
```

- [ ] **Step 3: Stack season/episode selectors on mobile**

Find the season selector container (around line 246):
```tsx
<div className="flex flex-wrap gap-4 items-end">
```

Replace with:
```tsx
<div className="flex flex-col sm:flex-row sm:items-end gap-3">
```

Find the episode grid container (around line 290):
```tsx
<div className="grid grid-cols-1 md:grid-cols-2 gap-3">
```
This is already responsive — no change needed.

Find the content type toggle container (around line 357):
```tsx
<div className="flex items-center gap-3 pt-2 border-t border-border/30">
```

Replace with:
```tsx
<div className="flex flex-col sm:flex-row sm:items-center gap-3 pt-2 border-t border-border/30">
```

- [ ] **Step 4: Verify build**

Run: `cd frontend && npm run build`
Expected: PASS with no errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Detail.tsx
git commit -m "feat: add synopsis expand/collapse, fix torrent names, stack selectors on mobile"
```

---

### Task 5: DownloadMonitor — Stack Action Buttons on Mobile

**Files:**
- Modify: `frontend/src/components/DownloadMonitor.tsx`

**Goal:** On mobile, stack action buttons below the title/status info instead of squeezing them side-by-side.

- [ ] **Step 1: Update download card header layout**

Find the card header section (around line 86-144). The current structure is:
```tsx
<div className="flex items-center justify-between mb-4">
  <div className="flex items-center gap-3 min-w-0">
    {/* status icon + title */}
  </div>
  <div className="flex items-center gap-2 flex-shrink-0">
    {/* action buttons */}
  </div>
</div>
```

Replace the outer wrapper div with:
```tsx
<div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
  <div className="flex items-center gap-3 min-w-0">
    {/* status icon + title — keep existing content */}
  </div>
  <div className="flex items-center gap-2 flex-shrink-0 sm:self-auto self-end">
    {/* action buttons — keep existing content */}
  </div>
</div>
```

This stacks the action buttons below the title on mobile, and keeps them side-by-side on desktop.

- [ ] **Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: PASS with no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/DownloadMonitor.tsx
git commit -m "fix: stack download action buttons on mobile screens"
```

---

### Task 6: SearchBar — Stack Input and Button on Mobile

**Files:**
- Modify: `frontend/src/components/SearchBar.tsx`

**Goal:** On mobile, stack the search input and "Buscar" button vertically so the button doesn't overflow the viewport.

- [ ] **Step 1: Update SearchBar layout**

Replace the entire `SearchBar.tsx` with:

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
        <div className="relative flex flex-col sm:flex-row items-stretch glass rounded-2xl
                      focus-within:ring-2 focus-within:ring-primary/30
                      focus-within:border-primary/30
                      transition-all duration-300 overflow-hidden">
          <div className="flex items-center flex-1">
            <Search className="w-5 h-5 text-muted-foreground ml-4 shrink-0" />
            <input
              type="text"
              placeholder="Buscar filmes, séries ou animes..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="flex-1 bg-transparent border-none outline-none
                       px-3 py-4 text-foreground placeholder:text-muted-foreground/60
                       font-body text-base"
            />
          </div>
          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="sm:ml-2 mx-2 mb-2 sm:mb-2 sm:mr-2 px-6 py-3 rounded-xl bg-primary text-primary-foreground
                     font-medium text-sm
                     hover:bg-primary/90 hover:shadow-lg hover:shadow-primary/20
                     active:scale-[0.98]
                     disabled:opacity-50 disabled:cursor-not-allowed
                     transition-all duration-200 flex items-center justify-center gap-2"
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

Key changes:
- Inner container: `flex flex-col sm:flex-row items-stretch`
- Input wrapped in a flex row div with the search icon
- Button gets full-width on mobile, side-by-side on desktop
- Added `overflow-hidden` to keep rounded corners clean

- [ ] **Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: PASS with no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/SearchBar.tsx
git commit -m "fix: stack search input and button vertically on mobile"
```

---

### Task 7: Settings Page — Fix Infinite Loading + Mobile Layout

**Files:**
- Modify: `frontend/src/pages/Settings.tsx`

**Goal:** Fix the infinite loading issue on mobile and stack input + Browse button on small screens.

- [ ] **Step 1: Fix the useEffect that may cause infinite re-renders**

The current useEffect syncs `pathValues` from API data. The dependency array uses specific fields which could cause issues. Add a guard to prevent unnecessary updates:

Current useEffect (around line 42-51):
```tsx
useEffect(() => {
  if (currentSettings?.data) {
    setPathValues((prev) => ({
      ...prev,
      movies_path: currentSettings.data.movies_path || '',
      series_path: currentSettings.data.series_path || '',
      animes_path: currentSettings.data.animes_path || '',
    }));
  }
}, [currentSettings?.data?.movies_path, currentSettings?.data?.series_path, currentSettings?.data?.animes_path]);
```

Replace with:
```tsx
useEffect(() => {
  if (currentSettings?.data) {
    const newValues = {
      movies_path: currentSettings.data.movies_path || '',
      series_path: currentSettings.data.series_path || '',
      animes_path: currentSettings.data.animes_path || '',
    };
    setPathValues((prev) => {
      // Only update if values actually changed
      if (
        prev.movies_path === newValues.movies_path &&
        prev.series_path === newValues.series_path &&
        prev.animes_path === newValues.animes_path
      ) {
        return prev;
      }
      return { ...prev, ...newValues };
    });
  }
}, [currentSettings?.data?.movies_path, currentSettings?.data?.series_path, currentSettings?.data?.animes_path]);
```

- [ ] **Step 2: Stack input + Browse button on mobile**

Find the input + Browse container (around line 158):
```tsx
<div className="flex gap-2">
  <input ... />
  <Button ...>Browse</Button>
</div>
```

Replace with:
```tsx
<div className="flex flex-col sm:flex-row gap-2">
  <input
    type="text"
    value={pathValues[setting.key] ?? currentValues[setting.key] ?? ''}
    placeholder={setting.placeholder}
    onChange={(e) => setPathValues((prev) => ({ ...prev, [setting.key]: e.target.value }))}
    onBlur={(e) => handleUpdate(setting.key, e.target.value)}
    className="flex-1 px-4 py-3 rounded-xl glass bg-transparent
             border border-border/50
             focus:outline-none focus:ring-2 focus:ring-primary/30
             focus:border-primary/30
             text-foreground placeholder:text-muted-foreground/50
             font-mono text-sm
             transition-all duration-200"
  />
  <Button
    type="button"
    variant="outline"
    size="default"
    className="shrink-0 sm:w-auto w-full"
    onClick={() => setPickerOpen(setting.key)}
  >
    <Folder className="w-4 h-4 mr-1" />
    Browse
  </Button>
</div>
```

- [ ] **Step 3: Make the settings grid responsive**

The grid at line 99 is already `grid grid-cols-1 lg:grid-cols-2` — good for mobile.

- [ ] **Step 4: Verify build**

Run: `cd frontend && npm run build`
Expected: PASS with no errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Settings.tsx
git commit -m "fix: prevent settings infinite re-render loop, stack inputs on mobile"
```

---

### Task 8: Final Verification

**Files:**
- All modified files

- [ ] **Step 1: Run full frontend build**

Run: `cd frontend && npm run build`
Expected: PASS with no errors

- [ ] **Step 2: Run ESLint**

Run: `cd frontend && npm run lint`
Expected: PASS with no errors

- [ ] **Step 3: Final commit (if any remaining changes)**

```bash
git status
```

If there are any uncommitted changes, commit them.

- [ ] **Step 4: Summary of all changes**

Files modified:
| File | Changes |
|------|---------|
| `frontend/src/components/ui/sheet.tsx` | New — Sheet component for mobile drawer |
| `frontend/src/components/Header.tsx` | Hamburger menu + Sheet drawer for mobile |
| `frontend/src/App.tsx` | Responsive container padding |
| `frontend/src/pages/Detail.tsx` | Synopsis expand, torrent names, stacked selectors |
| `frontend/src/components/DownloadMonitor.tsx` | Stacked action buttons on mobile |
| `frontend/src/components/SearchBar.tsx` | Stacked input + button on mobile |
| `frontend/src/pages/Settings.tsx` | Fixed re-render loop, stacked inputs on mobile |
