# Stock Management System — Localization (i18n)

**Status:** v1 implemented
**Languages:** English (`en`, default + fallback), Arabic (`ar`, generic — RTL)
**Last Updated:** 2026-05-07

---

## 1. Summary of Changes

- Added `react-i18next` + `i18next` + `i18next-browser-languagedetector` for runtime translation.
- Bundled `@fontsource/inter` (Latin) and `@fontsource/cairo` (Arabic) so the app works offline in Electron.
- Built a 13-namespace translation system under [frontend/src/i18n/locales](frontend/src/i18n/locales).
- Added `<LanguageSwitcher>` in the top nav with `localStorage` persistence (`stock_locale_v1`).
- Direction syncs automatically via `useDirection()` — sets `<html dir>` and `<html lang>`.
- All directional CSS rewritten with logical properties (`inset-inline-end`, `margin-inline-end`, `text-align: start`, `padding-inline-end`).
- All 10 pages + `ProductForm` consume `useTranslation()` — zero hardcoded user-facing strings.
- Locale-aware number/date formatting via `frontend/src/i18n/format.ts` (Western digits in both languages, per project decision).
- Axios interceptor errors are localized with sensible fallbacks (network/unauthorized/generic).

---

## 2. Architecture

```
frontend/src/
  i18n/
    index.ts              # i18next init, eager-loads JSON via import.meta.glob
    format.ts             # Intl.NumberFormat / DateTimeFormat helpers
    locales/
      en/                 # 13 namespaces (common, nav, auth, dashboard,
      ar/                 #  products, receiving, returns, reservations,
                          #  suppliers, purchaseOrders, reports, admin,
                          #  enums, toast)
  hooks/
    useDirection.ts       # syncs <html dir> + <html lang> on language change
  components/
    LanguageSwitcher.tsx  # nav-bar EN/العربية toggle
```

### Key conventions
- **Namespace per screen** (+ shared `common`, `enums`, `toast`).
- **Semantic keys**: `products.form.sku`, `enums.status.active`, never `addProductButton123`.
- **Backend identifiers stay English**: roles, statuses, ledger types, dispositions, return reasons, UoM are sent/received as English values; display labels go through `enums.<group>.<value>`.
- **ICU plural / interpolation** via i18next's native `{{var}}` and `count`-based plural rules. Arabic's CLDR plural forms are handled automatically.

---

## 3. Modified / Added Files

### Added
- `frontend/src/i18n/index.ts`
- `frontend/src/i18n/format.ts`
- `frontend/src/i18n/locales/{en,ar}/{common,nav,auth,dashboard,products,receiving,returns,reservations,suppliers,purchaseOrders,reports,admin,enums,toast}.json`
- `frontend/src/hooks/useDirection.ts`
- `frontend/src/components/LanguageSwitcher.tsx`

### Modified
- `frontend/package.json` — added i18n + font deps
- `frontend/src/main.tsx` — fonts + `import "./i18n"`
- `frontend/src/App.tsx` — nav uses `t()`, mounts `useDirection()` and `<LanguageSwitcher>`
- `frontend/src/api.ts` — interceptor uses translated fallback messages
- `frontend/src/styles.css` — Arabic font, `dir="rtl"` rule, logical-property sweep
- `frontend/src/components/ProductForm.tsx`
- `frontend/src/pages/{Login,Dashboard,Products,Receiving,Returns,Reservations,Suppliers,PurchaseOrders,Reports,Admin}Page.tsx`

---

## 4. RTL Approach

- Single switch point: `useDirection()` sets `document.documentElement.dir` and `lang` from `i18n.language`.
- **CSS** uses logical properties only — no `[dir="rtl"]` overrides for layout. The single override is `.lang-switcher` arrow padding (caret stays on the visual end).
- Arabic font (`Cairo`) is applied via `html[dir="rtl"] body`.
- Tables use `text-align: start` so headers and cells flip naturally.
- Toast position uses `inset-inline-end` so it appears bottom-left in RTL, bottom-right in LTR.
- Flex/grid `gap` is symmetric, no manual flipping needed.

---

## 5. Number / Date Formatting

- `formatNumber(value, opts?)` — `Intl.NumberFormat`, `numberingSystem: "latn"` so SKUs/quantities stay readable next to Latin IDs.
- `formatDate(value)` — short month + numeric day/year.
- `formatDateTime(value)` — adds 24h time.
- `formatBytes(n)` — backups column.
- All accept `null/undefined` and return `—`.

Per project decision (Q3 in proposal): **Western digits in both EN and AR** to preserve consistency with backend SKUs and IDs. Switching to Arabic-Indic digits later requires only removing `numberingSystem: "latn"` in `format.ts`.

---

## 6. Remaining Issues / Caveats

- **Backend error messages** from FastAPI are still English. The interceptor surfaces server messages verbatim when present; only the fallback (no response, 401, generic) is localized. Translating server error codes requires a code → key mapping (recommended for v2; backend should return stable error codes, not free-form messages).
- **`window.confirm()`** is still used in two places (`ReservationsPage.release`, `AdminPage.doRestore`). The browser confirm dialog uses OS chrome and ignores `dir` — text is translated but layout is OS-controlled. Replacing with a custom confirm modal would give full RTL visual fidelity.
- **Login default credentials** (`admin@example.com`, `ChangeMe123!`) are still hardcoded in `LoginPage` — these are dev seeds, not user-facing strings, so left alone.
- **Page `<title>`** in `index.html` is not yet bound to i18n — set once at boot. If desired, a small `useEffect(() => { document.title = t('appName') }, [i18n.language])` in `App.tsx` would fix it.
- **PO supplier column** displays raw supplier ID (`#123`). This pre-existed; not a localization issue but a data-fetching gap.

---

## 7. QA Checklist

Run in both `en` and `ar` (use the nav switcher):

- [ ] Nav links read in target language; switcher persists across reload (`localStorage`).
- [ ] `<html dir>` flips between `ltr` / `rtl` on switch.
- [ ] Toast appears bottom-right in EN, bottom-left in AR.
- [ ] Tables: headers and cell text align to leading edge in both modes.
- [ ] Login form flips: labels above inputs, button below; no overflow with Arabic placeholder lengths.
- [ ] Dashboard stat cards do not clip Arabic labels (24px stat-value + 11px stat-label).
- [ ] Products search bar + "+ New product" button remain on the same line; "+ New" sits at the trailing edge in both modes.
- [ ] Receiving line table inputs (qty 80px) don't clip, "Remove" / "إزالة" button fits.
- [ ] Returns disposition modal: select shows translated reasons/dispositions; backend payload still uses English values.
- [ ] Reservations expiry color (red < 7d) renders correctly in both modes.
- [ ] Admin metrics line wraps cleanly with the longer Arabic ICU template.
- [ ] PO modal width 640px holds the table without horizontal scroll in AR.
- [ ] Reports: format select shows CSV/JSON; status pill shows translated label, payload still sends `format=csv`.
- [ ] Confirm dialogs (release reservation, restore backup) read in target language.
- [ ] Mixed content: SKU `WIDGET-001` inside Arabic toast does not visually mirror.
- [ ] No raw English keys (`products.form.sku`) leaking through — would indicate a missing translation.

---

## 8. Scalability — Adding a Third Language

To add e.g. French:

1. Create `src/i18n/locales/fr/*.json` (copy `en/*.json`, translate values).
2. Add `"fr"` to `SUPPORTED_LNGS` in `src/i18n/index.ts`.
3. Add `<option value="fr">Français</option>` to `LanguageSwitcher`.
4. If RTL: add the `lng.startsWith("xx")` check to `isRTL()` in `i18n/index.ts`.
5. If a non-Latin font is needed: add `@fontsource/...` import to `main.tsx` and an `html[lang^="xx"] body { font-family: ... }` rule.

No code changes to pages, components, or API — they all key on the i18next runtime.

### Recommended next steps
- **Typed translations**: add `src/i18n/types.d.ts` augmenting `react-i18next` `Resources` to give `t()` autocomplete and compile-time safety. Skipped in v1 to keep the diff small; trivial to add later.
- **Backend error codes**: have FastAPI return stable string codes (e.g. `error.code = "stock.insufficient"`) and map on the frontend via `t(`errors.${code}`, defaultValue: serverMsg)`.
- **Per-user language** persisted server-side once user-preference endpoints exist.
- **Lazy namespace loading** (`i18next-http-backend`) once translations grow large enough that eager-loading every page's strings hurts startup. Today's bundle is small; eager is fine.
- **Currency / measurement units**: introduce `formatCurrency(value, code)` in `format.ts` when the v2 sales module lands.

---

## 9. How to Run

After pulling this branch:

```bash
cd frontend
npm install            # picks up new deps
npm run dev            # http://localhost:5173
```

Toggle the language via the **EN / العربية** select in the top-right of the nav.
