# RAGForge Documentation Website

Built with [Docusaurus 3](https://docusaurus.io/).

## Local Development

```bash
cd website
npm install
npm run start
```

This starts a local development server at `http://localhost:3000` with hot reload.

## Build

```bash
npm run build
```

Generates static content into the `build/` directory. This can be served by any static hosting service.

## Deployment

The site deploys to GitHub Pages automatically on push to `main` via the workflow at `.github/workflows/docs.yml`.

To deploy manually:

```bash
GIT_USER=<Your GitHub username> npm run deploy
```

## Structure

```
website/
├── docs/               # Documentation pages (MDX)
│   ├── getting-started/
│   ├── core-concepts/
│   ├── guides/
│   ├── any-language/
│   └── reference/
├── src/
│   ├── css/            # Custom styles
│   └── pages/          # Homepage and custom pages
├── static/             # Static assets
├── docusaurus.config.ts
├── sidebars.ts
└── package.json
```

## Adding Documentation

When a new module ships:
1. Update the guide from "Coming soon" stub to full documentation
2. Update the feature card on the homepage to show "Available"
3. Add API endpoints to the HTTP API reference
4. Run `npm run build` to verify
