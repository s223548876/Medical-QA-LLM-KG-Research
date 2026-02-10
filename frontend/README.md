# Frontend (Vite + React)

## Local development

```bash
cd frontend
npm install
npm run dev
```

## Runtime config

Edit `public/config.js`:

```js
window.__CONFIG__ = window.__CONFIG__ || {
  API_BASE_URL: "https://your-api-host",
  API_KEY: "your-api-key"
};
```

`src/App.jsx` reads `window.__CONFIG__` on startup, so API endpoint and key are not hardcoded in source.

## Build

```bash
cd frontend
npm run build
```

Build output is in `frontend/dist`.

## GitHub Pages base path

`vite.config.js` uses:
- `VITE_BASE_PATH` if provided
- otherwise `/${repoName}/` (repoName from `GITHUB_REPOSITORY`, fallback: `/medical_demo/`)

If your repository name is not `medical_demo`, either:
1. Set `VITE_BASE_PATH=/<your-repo-name>/` before build, or
2. Update the fallback in `frontend/vite.config.js`.

## GitHub Actions deploy

Workflow file: `.github/workflows/deploy-frontend.yml`

It builds `frontend` and deploys `frontend/dist` to GitHub Pages with:
`VITE_BASE_PATH=/${{ github.event.repository.name }}/`
