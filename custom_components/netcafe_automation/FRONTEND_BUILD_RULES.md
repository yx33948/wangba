# Frontend Build Rules

## Core Rule

- Frontend source files must be edited in `www_dev` first.
- Do not manually edit release files in `www` unless explicitly doing emergency debugging.
- After any frontend change, run the build pipeline to generate the latest files into `www`.

## Required Flow

1. Edit files under `www_dev`
2. Verify the change in `www_dev`
3. Run:

```bash
cd www_dev
npm run build:release
```

4. Confirm the build output has been written to:
   - `www`
   - `www_release`

## Directory Meaning

- `www_dev`: frontend development source of truth
- `www`: production files used by the integration
- `www_release`: release mirror output

## Working Agreement

- Any UI, JS, CSS, or HTML change should default to `www_dev`
- If a page looks wrong in `www`, first check whether `www_dev` was built
- When reporting completed frontend work, mention both:
  - which `www_dev` files were changed
  - that `npm run build:release` has been executed

## Short Reminder

Frontend changes should follow this rule:

`www_dev -> npm run build:release -> www`
