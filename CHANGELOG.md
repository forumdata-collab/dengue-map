# Changelog

所有重要變更都會記錄在此檔案。

格式依循 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/)，版本依循 [Semantic Versioning](https://semver.org/lang/zh-TW/)。

## [1.0.0] - 2026-09-22

### Added
- Three.js 3D 擠出地圖：62 個監察地區 × 60 個月（2021-09 → 2026-08）誘蚊器指數（AGI）及密度指數（ADI）
- 官方四級顏色（綠 / 黃 / 紅 / 紫）及高度對應指數
- 時間滑桿 + 自動播放、AGI/ADI 指標切換、19 區議會地區篩選
- hover tooltip（手動投影）+ 點擊詳情卡（歷史 sparkline）
- 全港每月平均指數趨勢圖（點擊跳轉月份）
- 頁底「預防蚊患」資訊卡（節錄自食環署《防治蚊患忠告》）
- 即時資料更新：CSDI 新月份探針 + 全量拉取重建
- 手機適配排版（地圖 hero 60vh + 控制項自然流）
- `build_data.py` 資料管線：分頁拉取、幾何去重、投影 offset

[1.0.0]: https://github.com/forumdata-collab/dengue-map/releases/tag/v1.0.0
