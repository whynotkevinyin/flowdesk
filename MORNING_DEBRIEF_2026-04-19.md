# 早安 Kevin — 昨晚的進度

你昨晚問的三件事，我全部做完了，測試也過了。睡前把看到的東西挑重點讀一下就好，詳細的在 `SECURITY.md` 和測試腳本裡。

---

## 1. 搜尋 bar + Jump to 為什麼沒反應 ✅ 已修

**原因：** 兩個都沒接 handler。Topbar 的搜尋只過濾 Tasks 畫面，切到其他 view 就失靈；Jump to 按鈕完全沒有 click listener。⌘K 也沒實作。

**現在：** 全部統一成 Linear / VSCode 風格的 **Command Palette**：
- 點 Jump to、點 topbar 搜尋框、打字、或按 ⌘K / Ctrl+K — 都會開啟
- 一次搜四個來源：**Tasks / Notes / Events / Flows**，匹配字會高亮
- ↑↓ 鍵選擇，Enter 跳過去（任務會 scroll + 閃黃）
- ESC 關閉
- 空白狀態顯示 hint + 最近的 8 個 flows 讓你快速跳轉

**測試：** `qa_palette.py` — 10 個測試全過。

**相關截圖：**
- `qa_morning_shots/02_palette_empty.png`
- `qa_morning_shots/03_palette_audit.png`（打「audit」，2 tasks + 1 note + 1 event + 1 flow）
- `qa_morning_shots/04_palette_Q2.png`（打「Q2」）
- `qa_morning_shots/06_tasks_filtered_via_palette.png`（從 palette 點 flow → 跳到 Tasks 且套用 filter）

---

## 2. 登入 log ✅ 已加

**新增一個獨立的 Security log**（沒跟 Activity log 混在一起，因為性質不同）：
- 記錄 6 種事件：`login_ok` / `login_fail` / `login_error` / `logout` / `autologin_ok` / `rate_limit`
- 每筆有 timestamp、事件類型、說明、User-Agent、platform、語系
- 最多保留 200 筆（ring buffer）
- 存在 `localStorage.flowdesk_security_log`

**怎麼看：** 右下角新增 🛡️ **Security** 按鈕（在 🔒 Logout 旁邊）。點開會看到：
- 有顏色分類的事件列表（綠/紅/橙/藍）
- 最上面顯示 summary：成功 / 失敗 / 自動登入 次數、最近失敗次數、是否被鎖定
- 可以 **Export JSON**（做審計用）或 **Clear log**

**相關截圖：** `qa_morning_shots/05_security_log.png`

---

## 3. 登入機制安全性評估 + 強化

### 你問：別人用 DevTools 會不會看到密碼？

**改動前：會，有四個地方看得到：**
1. Network tab → URL 的 `?key=XXX`
2. Application tab → Local Storage
3. Elements tab → `<input value="XXX">`（輸入後點 Unlock 前）
4. Sources tab → 變數視窗

**這次能在 Web 端修的我都修了：**

| 風險 | 修了沒 | 做法 |
|---|---|---|
| R3 密碼停留在 input 元素 | ✅ | 登入成功或失敗都 `input.value = ''` |
| R4 沒有 audit trail | ✅ | Security log（上面那個）|
| R5 沒有速率限制 | ✅ | 10 分鐘內 5 次失敗 → 鎖 5 分鐘，鎖定期間連 fetch 都不發 |
| R1 密碼出現在 URL query | ❌ 需改 Code.gs | 見 SECURITY.md §3 P0 |
| R2 localStorage 存明文 | ❌ 需改 Code.gs | 見 SECURITY.md §3 P1/P2 |

**需要你決定的：** R1 / R2 要改動 **Google Apps Script 後端**，我沒有直接碰，因為改錯會把所有裝置鎖在外面。建議做的優先順序是 **P0 最先**（把 key 從 URL 移到 POST body），`SECURITY.md` 裡有完整 patch 範例。

**測試：** `qa_security.py` — 19 個測試全過，包含：
- login_ok / login_fail / autologin_ok / logout / rate_limit 事件正確記錄
- 速率限制鎖定後連 fetch 都不發
- 密碼不會殘留在 DOM
- Security log 不含密碼字串
- Modal UI、Export、Clear 都正常

---

## 檔案總覽

新增／修改：
- `mnt/Flowdesk/index.html` — 主程式（palette + security log + rate limit）
- `mnt/Flowdesk/SECURITY.md` — 完整的安全性盤點 + 下一輪建議
- `mnt/Flowdesk/MORNING_DEBRIEF_2026-04-19.md` — 這份
- `mnt/Flowdesk/qa_morning_shots/` — 6 張截圖
- `qa_palette.py`（10 tests，全過）
- `qa_security.py`（19 tests，全過）

---

## 下一步（等你的 OK）

1. **把 key 從 URL 移到 POST body（P0）** — 這是最該做的，改完 DevTools Network tab 就看不到密碼了
2. **客戶端 SHA-256 hash + 時戳 nonce（P1）** — 防止 request replay
3. **Session token（P2）** — 真正的企業級做法

每一項都要同時改 Web 跟 Code.gs，看你想先從哪一個開始，我就把 patch 寫好給你 review。

早安 ☕️
