# V1.1 Mobile Shell

**Phase:** PHASE 2 — P0 Mobile Shell
**Branch:** `v1.1-productization`
**Scope:** browser viewport / safe-area model, bottom navigation placement, content
clearance, Coach composer relationship, Streamlit chrome, browser-storage surface.
**Out of scope (untouched):** readiness engine, training recommendation, safety logic,
persistence semantics, demo data, AI behaviour, page-level redesigns.

---

## 1. What was wrong (Phase 1 findings)

Three independent causes, verified with DOM geometry in the V1.0 build:

1. **The fixed bottom navigation covered live content.** The app reserved space only at the
   *end* of the document (`.block-container { padding-bottom: 6.6rem }`), so anything that
   happened to be in the last ~60 px of the viewport was painted over — including the Today
   `View workout` call to action (0 % / 16 % / 33 % visible at 375 / 390 / 393, centre hit
   test returned the nav).
2. **`env(safe-area-inset-bottom)` could never fire.** Streamlit writes
   `width=device-width, initial-scale=1, shrink-to-fit=no` with no `viewport-fit=cover`, so
   the inset reports `0` and the navigation kept only 7.2 px at the bottom edge.
3. **Coach had a second bottom bar.** `st.chat_input` renders a sticky `stBottom` dock; the
   custom nav (z-index 1000) was drawn over 59.9 px of it.

Plus two shell-level leaks: Streamlit chrome (`Deploy`, ⋮ developer menu, a dead
sidebar-expand chevron) inside the consumer mobile shell, and the browser-storage
component's iframe occupying 24 px and printing its status text through the header.

---

## 2. Architecture

Five layers, each with one owner:

| Layer | File | Owns |
|---|---|---|
| Shell tokens + CSS contract | `styles.py` (`SHELL_TOKENS`, `SHELL_CSS`) | spacing contract, viewport reservation, navigation placement, chrome hiding |
| Browser bridge | `mobile_shell/` (`__init__.py`, `frontend/shell.js`) | `viewport-fit=cover`, dynamic-viewport/keyboard signal |
| Navigation component | `ui_components.py` (`mobile_bottom_nav_component`, `mobile_utility_nav_component`) | destinations, labels/icons, active state |
| App wiring | `app.py` (`render_bottom_navigation`, `render_mobile_utility_nav`, `mobile_shell_bridge()`) | session-state routing only |
| Storage surface | `browser_storage/frontend/*` | IndexedDB sync, invisible presentation |

No page adds its own bottom offset: the shell is a single rule set.

---

## 3. The spacing contract

Tokens are generated from Python (`styles.SHELL_TOKENS`) into the document, so Python and
CSS cannot drift:

| Token | Value | Meaning |
|---|---|---|
| `--ara-nav-content-h` | `56px` | navigation row height |
| `--ara-shell-floor` | `8px` | minimum bottom breathing room when the browser reports no inset |
| `--ara-block-gap` | `.7rem` | mobile vertical rhythm between top-level blocks |
| `--ara-safe-top` / `--ara-safe-bottom` | `env(safe-area-inset-*)`, default `0px` | real device insets |
| `--ara-shell-inset` | `max(--ara-safe-bottom, --ara-shell-floor)` | never flush with the screen edge |
| `--ara-nav-h` | `calc(--ara-nav-content-h + --ara-shell-inset)` | navigation band |
| `--ara-shell-bottom` | `--ara-nav-h` | space the scrolling viewport must leave free |

### 3.1 Content clearance (the actual fix)

Document-end padding cannot protect a fixed overlay. Instead the scrolling viewport itself
is shortened:

```css
[data-testid="stMain"], [data-testid="stAppScrollToBottomContainer"] {
  height: calc(100dvh - var(--ara-shell-bottom)) !important;
}
```

The navigation then occupies the reserved band below the scroll area, so **content can never
be behind it at any scroll position** — measured `hiddenBehindNavPx = 0` at 375, 390, 393,
430 and 768. A `100vh` declaration precedes the `dvh` one as a fallback for engines without
dynamic viewport units.

`[data-testid="stAppScrollToBottomContainer"]` is the same element as `stMain` but renamed by
Streamlit when a top-level `st.chat_input` exists. Both are targeted, and the test suite
guards the pair.

### 3.2 Mobile vertical rhythm

The injected stylesheet is itself a zero-height block, and Streamlit's default `1rem` block
gap sat above every page's first element. One central rule on mobile replaces it:

```css
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] { gap: var(--ara-block-gap) !important; }
.st-key-ara_stylesheet { display: none !important; }   /* the <style> keeps applying */
```

Desktop is untouched by both rules (they live inside the `max-width: 768px` media query).
This is a shell spacing decision, not a page redesign: no content was reordered, restyled or
removed.

---

## 4. Viewport and safe area

Streamlit exposes no hook for the viewport meta tag, so `mobile_shell/frontend/shell.js`
runs in a same-origin component iframe and:

1. rewrites the document's `meta[name="viewport"]` to
   `width=device-width, initial-scale=1, shrink-to-fit=no, viewport-fit=cover`;
2. re-applies it through a `MutationObserver`, because Streamlit re-renders its own tag;
3. toggles `ara-keyboard-open` on `<html>` when the visual viewport shrinks (on-screen
   keyboard), which releases the navigation band so the Coach composer can use the space;
4. reports frame height `0` and **never** writes a component value, so it can never cause a
   rerun.

If the script cannot run, the shell still works: every value above has a CSS-only fallback
(`env()` with an `8px` floor, deterministic nav height, keyboard handling simply absent).

**Effect of the keyboard contract** (measured by toggling the class):

| State | `--ara-shell-bottom` | scrolling viewport | navigation |
|---|---|---|---|
| default | `calc(56px + max(0px, 8px))` | `844 - 64 = 780 px` | visible |
| `ara-keyboard-open` | `0px` | `844 px` | translated out, `pointer-events: none` |

---

## 5. Coach composer relationship

`stBottom` is `position: sticky` **inside** the scroll container, so shortening the viewport
also moves the composer above the navigation band — the two bars no longer compete for the
same pixels (no z-index trickery: nav `z-index: 1000`, composer dock stays at `99`).

`[data-testid="stBottomBlockContainer"]` keeps `.85rem` of bottom padding on mobile instead
of Streamlit's `56px` browser-chrome allowance, because the navigation band now provides
that clearance.

Measured at 390×844: composer dock `630.4 → 780.0`, navigation `780 → 844`, **overlap 0 px**,
gap 0.0 px, send control hit-tests to itself, textarea focusable.

---

## 6. Streamlit chrome

Hidden on mobile only (desktop keeps its sidebar shell unchanged):

| Selector | Why | Note |
|---|---|---|
| `[data-testid="stHeader"]` | empty 60 px band that also let content bleed through its translucent background | content now starts at the top with `env(safe-area-inset-top)` padding |
| `[data-testid="stToolbar"]` | container for the two controls below | |
| `[data-testid="stAppDeployButton"]` | publishing artifact | |
| `[data-testid="stMainMenu"]` | developer ⋮ menu (Rerun / Settings / Print) | |
| `[data-testid="stSidebar"]` | superseded by the bottom navigation | |
| `[data-testid="stSidebarCollapsedControl"]` | legacy expand control (older Streamlit) | kept for version safety |
| `[data-testid="stExpandSidebarButton"]` | **current 1.56 testid**; V1.0 only hid the legacy one, so a dead chevron was visible after every rerun | verified hidden after reruns |

Selectors are exact testids (no attribute wildcards, no descendant-wildcard hiding), so
future components cannot be caught by them. `MOBILE_HIDDEN_CHROME_SELECTORS` in `styles.py`
is the single list, and a test asserts each entry is present in the CSS.

---

## 7. Browser storage surface

`browser_storage/frontend/index.html` + `storage.js` keep the identical IndexedDB protocol
(`load` / `save` / `clear`, same messages, same value shape) but no longer have a visible
surface:

* status element is screen-reader-only (`1px`, clipped) instead of 12 px body text;
* frame height is `0` (was `24`);
* `.st-key-browser_storage_bridge` is hidden, so the element adds no layout box.

Verified end to end in Chromium: create a `My Local Profile` → record written to IndexedDB →
reload → record still present **and** hydrated into the runtime (Today shows the local
profile's empty state). See the Phase 2 section of `V1_1_UX_AUDIT.md`.

---

## 8. How to adjust or revert

* Navigation height / breathing room / rhythm → edit `styles.SHELL_TOKENS` only.
* Safe area behaviour → `--ara-safe-*` tokens; do not add per-page padding.
* Keyboard behaviour → the `ara-keyboard-open` rules in `SHELL_CSS`.
* A Streamlit version bump that renames chrome testids → update
  `MOBILE_HIDDEN_CHROME_SELECTORS`; the accompanying test will fail until it is updated.
* Reverting the shell entirely → restore the `max-width: 768px` block from V1.0
  (`git show v1.0.0:styles.py`); the componentized navigation and the bridge are additive.

---

## 9. Boundaries

Chromium emulation proves layout logic, not device behaviour. Still **not verified** here:
real iOS Safari bottom-toolbar overlap, real `env()` values on hardware, on-screen keyboard
interaction, PWA/browser-chrome interaction. Those are re-stated in the Phase 2 section of
`docs/V1_1_UX_AUDIT.md`.
