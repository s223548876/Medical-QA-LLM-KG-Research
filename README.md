# Medical-QA-LLM-KG-Research

醫療問答研究系統，結合：
- FastAPI 後端 API
- Neo4j 知識圖譜查詢
- Ollama LLM 生成答案
- React (Vite) 前端（可部署到 GitHub Pages）

## 1. 專案重點

- 後端提供 `/demo/search`、`/query`、`/llm_only`、`/health`
- `/demo/search` 受 `X-API-KEY` 保護（由 `APP_API_KEY` 控制）
- CORS allowlist 由 `FRONTEND_ORIGINS` 控制
- 前端透過 `window.__CONFIG__` 讀取 `API_BASE_URL` 與 `API_KEY`，不把 API 寫死在程式碼

## 2. 專案結構

```text
.
├─ app/                    # FastAPI backend
│  ├─ main.py
│  ├─ routers/
│  ├─ services/
│  ├─ repositories/
│  ├─ clients/
│  └─ static/              # 舊版靜態前端
├─ frontend/               # React + Vite 前端
│  ├─ public/config.js
│  ├─ src/App.jsx
│  └─ vite.config.js
├─ docs/
│  └─ ARCHITECTURE.md
└─ .github/workflows/
   └─ deploy-frontend.yml  # GitHub Pages 自動部署 frontend
```

## 3. 環境變數（後端）

請先複製 `.env.example` 為 `.env`，再填值。

- `OPENAI_API_KEY`
- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`
- `OLLAMA_BASE_URL`
- `APP_API_KEY`
- `FRONTEND_ORIGINS`
  - 逗號分隔，例如：
  - `https://<username>.github.io,https://<username>.github.io/<repo>`

## 4. 後端本地啟動

```bash
cd app
pip install -r requirements.txt -r requirements-dev.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

健康檢查：

```bash
curl http://127.0.0.1:8000/health
```

## 5. 前端本地啟動（React + Vite）

```bash
cd frontend
npm install
npm run dev
```

預設開發網址通常是 `http://localhost:5173`。

## 6. 前端設定檔（重要）

檔案：`frontend/public/config.js`

```js
window.__CONFIG__ = window.__CONFIG__ || {
  API_BASE_URL: "https://your-backend-domain",
  API_KEY: "your-app-api-key"
};
```

說明：
- `API_BASE_URL`：後端 API 網址（例如 `https://api.example.com`）
- `API_KEY`：對應後端 `APP_API_KEY`

## 7. 前端 Build 與部署

### 本地 Build

```bash
cd frontend
npm run build
```

產物在 `frontend/dist`。

### GitHub Pages（已提供 workflow）

檔案：`.github/workflows/deploy-frontend.yml`

- push 到 `main` 後，會自動：
  - 安裝 `frontend` 相依套件
  - 執行 `npm run build`
  - 部署 `frontend/dist` 到 GitHub Pages

### Vite base path

檔案：`frontend/vite.config.js`

- 優先使用 `VITE_BASE_PATH`
- 否則使用 `/${repoName}/`
- workflow 會自動注入：
  - `VITE_BASE_PATH=/${{ github.event.repository.name }}/`

## 8. API 使用範例

```bash
curl -G "http://127.0.0.1:8000/demo/search" \
  -H "X-API-KEY: <APP_API_KEY>" \
  --data-urlencode "question=什麼是高血壓？"
```

## 9. 開發備註

- 本 repo 已在 `.gitignore` 排除大型模型資料夾 `app/models/`，避免超過 GitHub 單檔大小限制。
- 若需完整模型檔，建議另行管理（私有儲存、artifact、或模型下載流程）。

## 10. 參考文件

- 架構說明：`docs/ARCHITECTURE.md`
- 部署補充：`DEPLOYMENT.md`
