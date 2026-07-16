# Frontend — React + Vite

## State management

No Redux, no Zustand — plain React Context in `App.jsx`:

```jsx
const AppContext = createContext();
export const useApp = () => useContext(AppContext);
```

Context provides:
- `watchedMap` — `{ "tmdbId-mediaType": item }` object of all watched items
- `isWatched(tmdbId, mediaType)` — boolean check
- `toggleWatched(item)` — add/remove from watched list (calls API)
- `updateRating(tmdbId, mediaType, rating)` — set personal rating
- `setSelectedItem(item)` — opens DetailModal
- `addToast(message, type)` — show notification

Every component that needs global state uses `const { ... } = useApp()`.

## API layer (`src/api.js`)

All backend calls go through the `api` object. Pattern:

```js
api.search(query, mediaType, page)      // → GET /api/search
api.trending(mediaType, page)           // → GET /api/trending
api.details(mediaType, id)              // → GET /api/details/{type}/{id}
api.getWatched()                        // → GET /api/watched
api.addWatched(item)                    // → POST /api/watched
api.removeWatched(tmdbId, mediaType)    // → DELETE /api/watched/{id}/{type}
api.updateRating(tmdbId, mediaType, r)  // → PATCH /api/watched/{id}/{type}
api.getRecommendations(limit)           // → GET /api/recommendations
```

Image helpers:
```js
posterUrl(path, size)     // → https://image.tmdb.org/t/p/{size}{path}
backdropUrl(path)         // → https://image.tmdb.org/t/p/w1280{path}
```

When adding a new API call, add it here — never fetch directly from components.

## Component patterns

### MediaCard
The universal display unit. Accepts an `item` object (from TMDB or from watched list) and optional `showReason` boolean for recommendation context. Always renders poster, title, year, TMDB rating, media type badge, and watched checkmark if applicable.

Item shape expected:
```js
{
  id: number,              // or tmdb_id
  media_type: "movie"|"tv",
  title: string,           // or name (for TV)
  poster_path: string|null,
  vote_average: number,
  release_date: string,    // or first_air_date
  // optional for recommendations:
  recommended_by: string[],
}
```

### DetailModal
Opens when `setSelectedItem(item)` is called. Fetches full details from `/api/details/`. Shows backdrop, poster, metadata, cast, overview. Contains the "Ho visto questo" / "Rimuovi" toggle button and the StarRating component for personal rating.

Closes on Escape key, overlay click, or X button.

### Pages
- **DiscoverPage** — dual mode: trending (default at `/`) and search (at `/search`, `searchMode` prop). Has debounced search (400ms) and media type filter tabs.
- **WatchedPage** — reads from `watchedMap` context. Client-side filtering by type, search, and sorting (added date / rating / title A-Z).
- **RecommendationsPage** — calls `api.getRecommendations()` on mount and when `watchedCount` changes. Shows "Perché hai visto X" reason tags.

## Routing

```jsx
<Routes>
  <Route path="/"                element={<DiscoverPage />} />
  <Route path="/search"          element={<DiscoverPage searchMode />} />
  <Route path="/watched"         element={<WatchedPage />} />
  <Route path="/recommendations" element={<RecommendationsPage />} />
</Routes>
```

Sidebar nav in App.jsx uses `<NavLink>` with `end` prop on `/`.

## Design system (index.css)

All theming via CSS custom properties at `:root`. Dark cinema-inspired palette:

| Variable | Value | Use |
|----------|-------|-----|
| `--bg-primary` | `#0c0c14` | Page background |
| `--bg-secondary` | `#14141f` | Sidebar, modals |
| `--bg-card` | `#1a1a2a` | Cards |
| `--accent` | `#e09f3e` | Amber — buttons, active states, ratings |
| `--text-primary` | `#e8e6f0` | Main text |
| `--text-secondary` | `#9896a8` | Subtitles, metadata |
| `--success` | `#4ade80` | Watched badge |
| `--danger` | `#f87171` | Remove actions |

Typography:
- Display: `Playfair Display` (page titles, modal titles, logo)
- Body: `Inter` (everything else)

Key CSS classes:
- `.media-grid` — auto-fill grid, `minmax(170px, 1fr)`
- `.media-card` — poster card with hover lift
- `.filter-tabs` — segmented control (Tutti / Film / Serie)
- `.btn-primary` / `.btn-secondary` / `.btn-danger` — button variants
- `.search-bar` — input with icon
- `.modal-overlay` + `.modal-content` — detail popup
- `.empty-state` — centered icon + text for empty lists
- `.spinner` — CSS-only loading indicator

## Adding a new page

1. Create `src/pages/NewPage.jsx`
2. Add `<Route path="/newpath" element={<NewPage />} />` in App.jsx
3. Add entry to `navLinks` array in App.jsx (icon from lucide-react)
4. Use `useApp()` for state, `api.*` for data fetching
5. Follow existing pattern: page-header → controls → media-grid or empty-state

## Adding a new component

1. Create `src/components/NewComponent.jsx`
2. Use `useApp()` if it needs global state
3. No local CSS files — add classes to `index.css`
4. Export as default

## Important gotchas

- TMDB movie objects have `title` and `release_date`; TV objects have `name` and `first_air_date`. Always handle both: `item.title || item.name`.
- Watched items from the database use `tmdb_id` as the ID field; TMDB results use `id`. Components handle both: `item.tmdb_id || item.id`.
- `genre_ids` is stored as a JSON string in the DB but as an array from TMDB. The `addWatched` function in App.jsx does `JSON.stringify()`.
- Vite dev proxy (`vite.config.js`) forwards `/api` to `localhost:8000`. In production, Nginx does this.
