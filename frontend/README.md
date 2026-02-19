# LeColaz Platform – Frontend

This document defines the architecture, styling system, and development workflow for the LeColaz frontend.

The goal is long-term maintainability (2+ years), strict type safety, and predictable UI behavior.

## 1. Technical Stack

- React (Vite)
- TypeScript (strict mode)
- Tailwind CSS v3.4.x
- PostCSS + Autoprefixer
- ESLint (flat config)
- Prettier
- Optional: shadcn (component primitives)

## 2. Safety Systems

We rely on three independent safety layers.

### 2.1 TypeScript – Static Type Safety

Controlled by:

- `tsconfig.json` (project references)
- `tsconfig.app.json`
- `tsconfig.node.json`

Strict mode is enabled.

Before major changes:

```bash
npm run typecheck
```

(Type checking runs `tsc --noEmit`.)

Purpose:

- Prevents invalid imports
- Validates path aliases (`@/`)
- Enforces strict typing discipline

### 2.2 ESLint – Code Quality

Run:

```bash
npm run lint
```

Purpose:

- Detect React Hook violations
- Catch unused variables
- Enforce consistent patterns

Lint errors must be resolved before merging.

### 2.3 Prettier – Formatting

Run:

```bash
npm run format
```

Purpose:

- Prevent formatting conflicts
- Ensure consistent code style in PRs

## 3. Styling Architecture (Tailwind v3)

We use a token-based styling system.

No hardcoded colors are allowed in components.

### 3.1 Styling Pipeline

Tokens defined in:

- `src/styles/globals.css`

Tokens mapped to Tailwind utilities in:

- `tailwind.config.ts`

Components consume semantic utilities:

- `bg-background`
- `bg-card`
- `text-foreground`
- `text-muted-foreground`
- `border-border`
- `bg-primary`
- etc.

Tailwind JIT generates CSS based on class usage in:

```ts
content: ['./index.html', './src/**/*.{ts,tsx}'];
```

### 3.2 Token Definition

In `src/styles/globals.css`:

- `:root` defines light theme variables
- `:root.dark` overrides them for dark mode

Important:
Token variables are defined outside `@layer base` to ensure reliable application.

Dark mode is class-based:

```ts
darkMode: ['class'];
```

To activate manually:

```ts
document.documentElement.classList.add('dark');
```

### 3.3 What Is Not Allowed

Do NOT use:

- `bg-white`
- `bg-gray-*`
- `text-gray-*`
- raw hex colors
- inline style colors

All colors must come from tokens.

## 4. File Responsibilities

| File                                      | Responsibility                                                        |
| ----------------------------------------- | --------------------------------------------------------------------- |
| `src/styles/globals.css`                  | Global tokens, radius, motion variables, optional component-layer CSS |
| `tailwind.config.ts`                      | Maps CSS variables to Tailwind utilities                              |
| `postcss.config.js`                       | Tailwind + Autoprefixer integration                                   |
| `vite.config.ts`                          | Build configuration + path aliases                                    |
| `src/lib/utils.ts` (or `src/utils/cn.ts`) | `cn()` helper for safe class merging                                  |
| `src/components/ui/`                      | UI primitives (Button, Card, etc.)                                    |
| `App.tsx` / layout files                  | Layout composition only                                               |

## 5. `cn()` Utility

Location:

- `src/lib/utils.ts` 

Purpose:
Safely merge class names using:

- `clsx`
- `tailwind-merge`

Prevents class conflicts like:

- `px-2` + `px-4`

Usage:

```tsx
<div className={cn('base', isActive && 'active', className)} />
```

## 6. Shadcn Usage

We are on Tailwind v3.

If installing via CLI, use a v3-compatible version:

```bash
npx shadcn@2.3.0 init
```

Note:
If network/DNS prevents CLI usage, primitives can be created manually and Radix components installed individually as needed.

Shadcn components are copied into:

- `src/components/ui/`

They are source code, not a dependency black box.

You are allowed to edit them.

## 7. Development Workflow

Start dev server:

```bash
npm run dev
```

Before pushing code:

```bash
npm run format
npm run lint
npm run typecheck
```

Only push code that passes all three.

## 8. Dark Mode Policy

Current mode: class-based only.

We do not automatically follow system preferences yet.

This can be extended later.

## 9. Long-Term Rules

- Styling decisions live in tokens.
- Layout logic lives in components.
- Do not modify Tailwind version casually.
- Do not introduce global CSS outside `globals.css`.
- Prefer semantic utilities over raw Tailwind color utilities.

## 10. References

- Tailwind CSS v3 documentation
- shadcn (v3-compatible) documentation
- Radix UI documentation
- Vite documentation
