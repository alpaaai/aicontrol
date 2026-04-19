# AIControl Docs Site — Claude Code Build Brief

## What to build

A documentation site at `aictl.io/docs` within the existing Next.js + Vercel site repo (`github.com/alpaaai/aicontrol-site`).

The docs section is a new route added to the existing site. It does not replace the homepage. The homepage stays as-is.

---

## Source files

All markdown content is in `~/aicontrol/docs/public/`. Nine files:

```
00-navigation.md    ← page structure and slug map — read this first
01-overview.md      → /docs
02-getting-started.md → /docs/getting-started
03-integration.md   → /docs/integration
04-integrations.md  → /docs/integrations
05-policies.md      → /docs/policies
06-audit-log.md     → /docs/audit-log
07-api-reference.md → /docs/api-reference
08-operations.md    → /docs/operations
```

Read all nine files before writing any code.

---

## Tech stack

- Next.js (App Router) — already in use on the site
- Tailwind CSS — already in use
- `next-mdx-remote` or `@next/mdx` for rendering markdown
- `rehype-highlight` or `shiki` for code syntax highlighting — pick whichever is already installed; if neither, install `shiki`
- No new UI component libraries unless already present

---

## Routes to create

```
/docs                   → renders 01-overview.md
/docs/getting-started   → renders 02-getting-started.md
/docs/integration       → renders 03-integration.md
/docs/integrations      → renders 04-integrations.md
/docs/policies          → renders 05-policies.md
/docs/audit-log         → renders 06-audit-log.md
/docs/api-reference     → renders 07-api-reference.md
/docs/operations        → renders 08-operations.md
```

---

## Layout

Every `/docs/*` page uses a shared two-column layout:

```
┌──────────────────────────────────────────────────────────┐
│  [AIControl logo / wordmark]           [hello@aictl.io]  │  ← top nav (minimal)
├────────────────┬─────────────────────────────────────────┤
│                │                                         │
│   Sidebar      │   Page content                          │
│   (fixed,      │   (scrollable)                          │
│    ~240px)     │                                         │
│                │                                         │
└────────────────┴─────────────────────────────────────────┘
```

**Sidebar — fixed, left:**
- AIControl logo or wordmark at top
- Nav links matching the structure in `00-navigation.md`
- Active page highlighted
- Two sections with a visual separator: "Integration" group (How It Works + Framework Wrappers as a sub-item) and the rest flat

**Content area:**
- Max width ~720px, centered within the column
- Comfortable reading padding (px-8 or equivalent)
- H1 at top of each page
- H2 sections with visible weight
- Code blocks: dark background (`#0d1117` or equivalent), monospace font, copy button on hover
- Tables: clean, no zebra striping needed, just borders or subtle row lines
- No sidebar-style callout boxes needed — plain prose is fine

**Mobile:**
- Sidebar collapses to a hamburger/drawer on mobile
- Content is full-width

---

## Design requirements

Match the existing site's visual language. The site uses a light theme (white/light-gray background, dark text). Read `globals.css` to confirm exact values before setting any colors.

- Background: match existing site (white or light gray — read globals.css)
- Text: dark primary, muted gray for secondary — match existing site typography
- Sidebar active link: subtle left border accent using the site's existing accent color, darker text weight
- Code blocks: light gray background (`#f6f8fa` or equivalent), syntax highlighting via shiki `github-light` theme
- No gradients or decorative elements in the docs — clean, functional

Do not apply the homepage's hero/marketing styling inside docs pages.

---

## Code block requirements

This is the most important rendering concern. Engineers will copy code from these docs.

- Syntax highlighting for: `python`, `typescript`, `bash`, `json`, `sql`
- Copy button on each block — appears on hover, copies the raw code (no line numbers in clipboard)
- Line numbers are optional — omit if they add complexity
- Language label visible (e.g. "python", "bash") in top-right corner of block
- No wrapping — horizontal scroll on overflow

---

## Content rendering requirements

- Render all markdown as-is — do not alter any prose or code content
- Tables render as HTML tables — styled to fit the dark theme
- Internal links (`/docs/policies`, `/docs/integration`) must work as Next.js `<Link>` components
- No `[!NOTE]` callout syntax is used in the source — no special callout rendering needed

---

## File organization

```
app/
  docs/
    layout.tsx          ← shared two-column docs layout with sidebar
    page.tsx            ← /docs → overview
    getting-started/
      page.tsx
    integration/
      page.tsx
    integrations/
      page.tsx
    policies/
      page.tsx
    audit-log/
      page.tsx
    api-reference/
      page.tsx
    operations/
      page.tsx

content/
  docs/
    01-overview.md
    02-getting-started.md
    03-integration.md
    04-integrations.md
    05-policies.md
    06-audit-log.md
    07-api-reference.md
    08-operations.md
```

Copy the markdown files from `~/aicontrol/docs/public/` into `content/docs/` as the first step. Do not modify their content.

---

## Sidebar navigation data

Define this as a static config — do not generate from filesystem:

```typescript
// lib/docs-nav.ts
export const docsNav = [
  { title: "Overview", href: "/docs" },
  { title: "Getting Started", href: "/docs/getting-started" },
  {
    title: "Integration",
    children: [
      { title: "How It Works", href: "/docs/integration" },
      { title: "Framework Wrappers", href: "/docs/integrations" },
    ],
  },
  { title: "Policies", href: "/docs/policies" },
  { title: "Audit Log", href: "/docs/audit-log" },
  { title: "API Reference", href: "/docs/api-reference" },
  { title: "Operations", href: "/docs/operations" },
];
```

---

## Packages to install (if not already present)

```bash
npm install next-mdx-remote shiki
```

If `@next/mdx` is already configured, use that instead of `next-mdx-remote` — check `next.config.*` before installing anything.

---

## Build order

1. Copy markdown files from `~/aicontrol/docs/public/` into `content/docs/`
2. Check existing `package.json` and `next.config.*` for any MDX config already present
3. Install missing packages
4. Create `lib/docs-nav.ts` with the nav config above
5. Create `app/docs/layout.tsx` — the shared two-column layout with sidebar
6. Create a shared `MDXContent` component that renders markdown with shiki syntax highlighting
7. Create each `page.tsx` — each one reads its markdown file and renders via `MDXContent`
8. Add copy button behavior to code blocks
9. Verify all 8 routes render correctly with `npm run dev`
10. Verify internal links (`/docs/policies`, etc.) navigate correctly
11. Verify code blocks have syntax highlighting and copy button
12. Commit and push — Vercel will deploy automatically

---

## Verification checklist

Before pushing:

```
✓  /docs renders Overview content
✓  /docs/getting-started renders Getting Started content
✓  /docs/integration renders Integration content
✓  /docs/integrations renders all 8 framework wrappers with syntax highlighting
✓  /docs/policies renders Policies content
✓  /docs/audit-log renders Audit Log content
✓  /docs/api-reference renders API Reference content
✓  /docs/operations renders Operations content
✓  Sidebar shows on all /docs/* pages
✓  Active page is highlighted in sidebar
✓  Internal links work (e.g. clicking "Policies" from Overview navigates correctly)
✓  Code blocks have syntax highlighting (python, typescript, bash, json, sql)
✓  Code copy button works — clipboard contains raw code
✓  Mobile: sidebar collapses, content is readable
✓  No console errors
✓  Existing homepage (/) is unchanged
```

---

## What not to do

- Do not modify any content in the markdown files
- Do not add a search bar — out of scope for V1
- Do not add a table of contents sidebar — out of scope for V1
- Do not add versioning or tabs — single version, no tabs
- Do not add a footer to the docs layout — keep it clean
- Do not use a third-party docs framework (Nextra, Mintlify, Docusaurus) — build directly in Next.js

---

## Support

hello@aictl.io
