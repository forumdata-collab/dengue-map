# 登革熱病媒監察互動地圖 (Dengue Vector Surveillance Interactive Map)

食環署白紋伊蚊誘蚊器指數 Three.js 3D 互動地圖 — 全港監察地區每月數據，支援時間瀏覽、地區篩選與即時更新。

**Live:** https://forumdata-collab.github.io/dengue-map/

## ✨ Features

| 功能 | 實作細節 |
|------|----------|
| 3D 擠出地圖 | Three.js `ExtrudeGeometry`，柱高對應誘蚊器指數，顏色對應官方四級（綠 <5% / 黃 5–20% / 紅 20–40% / 紫 ≥40%） |
| 時間瀏覽 | 60 個月（2021-09 → 最新月份）滑桿 + 自動播放，月與月之間柱高/顏色即時切換 |
| 指標切換 | 誘蚊器指數（AGI）／密度指數（ADI）雙指標，圖例隨指標切換 |
| 地區篩選 | 19 個區議會地區，非所選地區自動淡化 |
| 互動詳情 | hover 即時 tooltip（手動投影，無 CSS2DRenderer 依賴）；點擊顯示該區歷史走勢 sparkline |
| 全港趨勢 | 每月平均指數折線圖，點擊可跳轉月份 |
| 即時資料 | 網頁載入時自動探測 CSDI 新月份（`orderByFields` 單請求探針），有更新即拉取重建，無需 cron |
| 手機適配 | 地圖 hero + 控制項自然流排版，無巢狀滾動；桌面版固定高度 dashboard |

## 📊 資料範圍

- 監察地區：62 個（2026 年；歷史上限 90 個名稱，地區重組會反映在對應月份）
- 欄位：`LOCATION`（監察地區）、`DISTRICT`（區議會地區）、`PERIOD`（YYYY-MM）、`AGI`（分區誘蚊器指數 %）、`ADI`（分區密度指數）
- 月份缺指數的地區自動隱藏（非顯示為 0）

## 🏗️ Architecture

```
index.html        單一檔案前端（Three.js 0.160 importmap + 內嵌 CSS/JS）
data.js           window.DENGUE_DATA — 62 區 × 60 月 + 已投影幾何（build_data.py 產出）
build_data.py     資料管線：CSDI FeatureServer → 分頁拉取 → 幾何去重 → 投影 offset
```

核心資料結構：

```js
window.DENGUE_DATA = {
  latest: "2026-08",
  periods: ["2021-09", ..., "2026-08"],
  areas: [{
    id, name: {tc, en}, district: {tc, en},
    parts: [{ring: [[x,z]...], holes: [...]}],   // 局部 Web Mercator，已 offset 至 bbox 中心
    center: [x, z],
    series: [[periodIdx, agi, adi], ...]         // 對齊 periods；null = 該月無數據
  }]
}
```

設計取捨（刻意保留）：
- 幾何在 build 時投影 + offset，瀏覽器只做顯示，float32 精度安全（座標 ±19km 內）
- 高度用 `scale.y` 驅動（預建 MAXH 幾何），滑桿拖動毋須重建 geometry
- tooltip 每 frame 手動投影，必須做 perspective divide（`clip.w`），唔依賴 CSS2DRenderer（rAF throttled 時會失效）

## 🔄 資料更新

CSDI ArcGIS FeatureServer（CORS 全開，瀏覽器可直接 fetch）：

```
https://portal.csdi.gov.hk/server/rest/services/common/fehd_rcd_1629966670823_4638/FeatureServer/0/query
?f=geojson&where=1=1&outFields=*&outSR=4326&resultOffset=<分頁>&resultRecordCount=3000
```

- 單請求上限 3000 條 → 分頁拉取
- 新月份探針：`returnGeometry=false&outFields=PERIOD&orderByFields=PERIOD%20DESC&resultRecordCount=1`
- 前端只在新月份存在時先全量拉取（2 批），否則用內嵌 snapshot

重建 snapshot：

```bash
python3 build_data.py   # 產出 data.js
```

## 🧪 Testing

```bash
python3 -m http.server 8899   # 然後瀏覽器開 http://localhost:8899/
```

驗證要點（browser tool）：
- WebGL2 context 存在、零 window error
- 方向：上水（北）螢幕上方、西貢（東）螢幕右方
- hover/click/slider/play/指標切換/地區篩選全部有 DOM 斷言
- 手機 viewport（390×844）：地圖 60vh hero、控制項自然流、無巢狀 scroll

已知測試注意：synthetic `PointerEvent` 會觸發 OrbitControls `setPointerCapture` NotFoundError（無 active pointer）—— 測試假象，真實輸入無影響。

## 🚀 Deploy

GitHub Pages（Actions workflow 自動建置，push main 即部署）：

```bash
git push origin main   # .github/workflows/pages.yml 自動跑
```

備用：Cloudflare Pages（`dengue-map-we1co.pages.dev`，`wrangler pages deploy . --project-name=dengue-map-we1co --branch=main`）。

## 📜 License

MIT © 2026 forumdata-collab

資料來源：食物環境衞生署（FEHD）登革熱病媒監察，經 data.gov.hk / 空間數據共享平台（CSDI）發佈，每月更新。本專案為資料視覺化，非官方網站；最新詳情以食環署公布為準。

---

[SECURITY.md](SECURITY.md) · [CHANGELOG.md](CHANGELOG.md)
