# 社區長期服務平台

社區居家關懷與志願服務平台。單體後端 + 雙前端的 monorepo：

- `backend/` — Django 4.2 + DRF + MySQL（本地可用 sqlite）。單一 REST API，同時服務兩個前端。
- `web-admin/` — Vue 3 + Vite + Element Plus + ECharts。管理後台 + 數據大屏。
- `harmony-app/` — HarmonyOS ArkTS/ArkUI 手機端，給居民與志願者使用（在 DevEco Studio 開啟/構建）。

兩個前端共用同一套 API，並以 `Authorization: Token <token>` 認證。程式碼註釋、界面文案、提交訊息均為中文。分項細節見 `web-admin/README.md`、`harmony-app/README.md`。

## 本地啟動流程

後端與 web 管理台在同一台機器上運行；HarmonyOS 模擬器透過 `10.0.2.2:8000` 連該機器的後端。

### 1. 後端（`cd backend`）

首次需準備虛擬環境與依賴：

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

資料庫：預設走 MySQL（`emergency_backend/settings.py`）。本地無 MySQL 時，在 `settings.py` 末尾追加一段 sqlite override 即可（此改動屬本地 tweak，不要提交）：

```python
# === LOCAL SQLITE OVERRIDE（本地跑用，勿提交）===
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
```

遷移並啟動（監聽 `0.0.0.0` 以便模擬器可達）：

```bash
python manage.py migrate
python manage.py seed_data          # 可選：造演示資料（admin/admin123，其餘 123456）
python manage.py runserver 0.0.0.0:8000
```

驗證：`curl -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/api/` 回 `401`（需認證）即正常。

### 2. Web 管理台（`cd web-admin`）

需 Node `^22.18.0 || >=24.12.0`（用 nvm 時先 `nvm use 24`）。

```bash
npm install
npm run dev
```

Vite 只綁定 `localhost`（含 IPv6），請用 `http://localhost:5173/` 開啟，勿用 `127.0.0.1`。需暴露到區域網時加 `npm run dev -- --host`。

後台登入：`admin / admin123`。API base URL 在 `src/api/request.js`（`baseURL`，預設 `http://127.0.0.1:8000/api`）。

### 3. HarmonyOS 模擬器 / App（`harmony-app/`）

在 DevEco Studio 開啟 `harmony-app/` 構建運行。後端地址為 `entry/src/main/ets/common/Api.ets` 的 `Api.BASE_URL`；模擬器連本機後端時設為 `http://10.0.2.2:8000`（此改動屬本地 tweak，不要提交）。

## 測試

```bash
cd backend
python manage.py test                 # 全部
python manage.py test users           # 單一 app
```

測試使用 `settings.py` 中配置的資料庫（同上，本地可臨時指向 sqlite，勿提交）。
