# Mobile Responsiveness Fix — Design Spec

## Context

The Jellyfin Automation frontend works well on desktop but has layout issues on mobile (Samsung S23, ~360px viewport). Three areas were identified as problematic: Header, Detail Page, and Downloads/Search/Settings pages.

## Approach

Hybrid approach (C): targeted fixes for critical issues + useful new functionality (synopsis "Read more") + responsive foundation improvements, without a full redesign.

## Changes by Component

### 1. Header — Mobile Navigation Drawer

**File:** `frontend/src/components/Header.tsx`

**Problem:** 6 nav icons + theme toggle + avatar overflow the ~360px viewport. Theme toggle and avatar are not visible at all on S23.

**Solution:**
- On mobile (<768px / `md` breakpoint): show the logo icon + app title "Jellyfin Automation" + hamburger menu button
- Hamburger opens a dropdown/drawer (using shadcn `Sheet` component) containing:
  - All 6 navigation links (with icons + labels)
  - Theme toggle
  - Avatar "JA"
- On desktop (≥768px): keep current layout unchanged

**New dependency:** `npx shadcn@latest add sheet` for the mobile drawer.

### 2. Detail Page — Synopsis & Torrent List

**File:** `frontend/src/pages/Detail.tsx`

**Problem A — Synopsis:** Text is truncated at `line-clamp-3` with no way to read the full text on mobile.

**Solution:**
- Keep `line-clamp-3` as default
- Add a "Ler mais" / "Ler menos" toggle button below the synopsis
- Use local state (`synopsisExpanded`) to toggle between clamped and full text
- Button appears only when text is actually clamped (or always, for simplicity)

**Problem B — Torrent names:** Long torrent names get truncated with `truncate` and the full name is not visible.

**Solution:**
- Change `truncate` to `break-all` on mobile for torrent titles
- Add `title` attribute for native tooltip on hover (desktop)
- In the detail dialog, `break-all` is already applied — no change needed there

**Problem C — Season/Episode selectors:** Flex row with gap wraps poorly on mobile.

**Solution:**
- Change `flex flex-wrap gap-4` to `flex flex-col sm:flex-row gap-3` for the season selector area
- Episode grid already uses `grid-cols-1 md:grid-cols-2` — acceptable

### 3. Downloads Page — Action Buttons

**File:** `frontend/src/components/DownloadMonitor.tsx`

**Problem:** Pause/resume/cancel buttons overlap on mobile because they sit in a flex row next to the title.

**Solution:**
- On mobile: move action buttons to a new row below the title/status info
- Use `flex-col sm:flex-row` on the card header
- Buttons get full-width or centered on mobile for easier tap targets (min 44px touch area)

### 4. Search Page — SearchBar Overflow

**File:** `frontend/src/components/SearchBar.tsx`

**Problem:** The "Buscar" button overflows the viewport because input + button don't fit in ~360px.

**Solution:**
- Change the inner flex container to `flex-col sm:flex-row` on mobile
- Input gets full width, button gets full width below it
- Adjust padding/margins accordingly for stacked layout
- On desktop: keep current side-by-side layout

### 5. Settings Page — Infinite Loading

**File:** `frontend/src/pages/Settings.tsx`

**Problem:** Page loads infinitely on mobile (likely a query loop or API issue, not purely visual).

**Investigation plan:**
- Check if `settingsAPI.getSettings()` returns properly on mobile network
- Check if the `useEffect` that syncs `pathValues` creates a render loop
- The `useEffect` dependency array uses specific fields (`movies_path`, `series_path`, `animes_path`) which could cause issues if the API returns `null` or different structure
- Fix: add a guard to prevent infinite re-renders

**Solution (if API-related):**
- Add error boundary or retry logic to the settings query
- Add a timeout or max-retry guard

**Solution (if layout-related):**
- Input + Browse button: stack vertically on mobile with `flex-col sm:flex-row`

### 6. App.tsx — Container Padding

**File:** `frontend/src/App.tsx`

**Problem:** `px-6 lg:px-12` and `pt-24` may be too much padding on mobile.

**Solution:**
- Change to `px-4 sm:px-6 lg:px-12` for tighter mobile margins
- Change `pt-24` to `pt-20 sm:pt-24` to reduce top padding on mobile

## Files Modified

| File | Changes |
|------|---------|
| `Header.tsx` | Hamburger menu + Sheet drawer for mobile nav |
| `Detail.tsx` | Synopsis expand/collapse, torrent name break-all, season selector stacking |
| `DownloadMonitor.tsx` | Action buttons stack on mobile |
| `SearchBar.tsx` | Input + button stack on mobile |
| `Settings.tsx` | Fix infinite loading, input + Browse stack on mobile |
| `App.tsx` | Responsive container padding |
| `index.css` | No changes needed (Tailwind handles breakpoints) |

## New Dependencies

- `@radix-ui/react-dialog` (already installed via shadcn)
- `npx shadcn@latest add sheet` — for mobile navigation drawer

## Testing

- Verify on Samsung S23 (360×780 viewport)
- Verify on desktop (1920×1080) — no visual regression
- Test hamburger menu open/close, navigation, theme toggle
- Test synopsis expand/collapse
- Test search form submission on mobile
- Test download action buttons tap targets
- Test settings page loads without infinite loop
