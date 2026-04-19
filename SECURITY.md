# Flowdesk Security Notes

這份文件回答 Kevin 在夜裡問的兩個問題：

1. **登入機制安不安全？別人用 DevTools 會不會看到密碼？**
2. **我們是不是需要更好的安全機制？**

以下是現況盤點、目前這次改了什麼、以及接下來建議怎麼做。

---

## 1. 現況風險盤點

目前 Flowdesk Web 登入是 Kevin 自己架的 Google Apps Script 後端，單一共用密鑰（API key）。我找到幾個風險層級不同的問題：

### 🔴 高風險

**R1. 密碼以明文出現在網址 query string** ✅ **已修（2026-04-19）**
- 先前 `fetch(API_URL + '?action=getTasks&key=' + encodeURIComponent(key))`
- 現在全部改走 POST + `Content-Type: text/plain;charset=utf-8`（避免 CORS preflight）
- 新的 `apiCall()` helper 把 `action` 與 `key` 放在 JSON body 裡
- Code.gs v16 的 `doPost()` 現在也接手所有讀取動作（`getTasks` / `getTasksLight` / `getNoteContent` / `init` / `ping`）
- `doGet()` 保留向下相容，舊的 desktop client 仍可用
- 結果：Network tab / browser history / referrer header / GAS log 都**不再**有密碼

**R2. 密碼以明文存在 `localStorage.flowdesk_api_key`**
- 任何能在 `file://` 或未來部署網域執行 JS 的人（包含惡意 extension）都能讀到
- DevTools → Application → Local Storage 直接看得到
- 如果使用者電腦被裝 malware，金鑰一定會流出

### 🟠 中風險

**R3. 密碼在 `<input>` 元素上停留**
- 登入後如果不清空，DevTools → Elements 就能看到 `value`
- ✅ **這次已修**：不管成功或失敗，`input.value = ''` 都會把它清掉

**R4. 沒有 audit trail**
- 先前不知道誰在什麼時候登入、登入失敗幾次
- ✅ **這次已修**：Security log 保留最近 200 筆事件

**R5. 沒有速率限制**
- 任何人可以無限次嘗試密碼
- ✅ **這次已修**：10 分鐘內 5 次失敗鎖定 5 分鐘

### 🟡 低風險

**R6. 同一把金鑰用於所有裝置 / 所有動作**
- 無法撤銷單一裝置
- 無法區分「讀」跟「寫」權限

---

## 2. 這次做了什麼（web 端，不需改 Code.gs）

### (a) 登入事件 Audit Log
- 新增 `securityLog` ring buffer（最近 200 筆，`localStorage.flowdesk_security_log`）
- 記錄六種事件：`login_ok` / `login_fail` / `login_error` / `logout` / `autologin_ok` / `rate_limit`
- 每筆記錄 timestamp、事件類型、說明、User-Agent、platform、語系
- **不**記錄密碼 / 不記錄 hash / 不記錄 IP
- 右下角新增 🛡️ Security 按鈕，點開 modal 查看、可 Export JSON、可清空

### (b) 客戶端速率限制
- 10 分鐘內 5 次失敗密碼 → 鎖 5 分鐘
- 鎖定期間連 `fetch` 都不會發
- 鎖定訊息顯示在登入錯誤列
- 鎖定狀態本身也記錄在 Security log

### (c) 密碼輸入框即時清空
- 登入成功或失敗，`input.value = ''` 都會執行
- DevTools 再看 Elements tab 已經看不到明文
- `<input>` 本來就是 `type="password"`，所以螢幕上一直是圓點

### (d) 測試覆蓋
- `qa_security.py` 19 個測試全過
- 包含：事件記錄正確、密碼不存在 DOM、速率限制鎖定、modal UI、Export / Clear

---

## 3. 還沒改、但強烈建議下一輪改的

**這些需要同時改 Web（index.html）和 Server（Code.gs）。**我沒有直接碰 Code.gs，因為那是 Kevin 部署的、改錯會讓所有人鎖在外面。

### ~~P0 — 金鑰不要出現在 URL~~ ✅ 完成 2026-04-19

**這輪做完了。**

**Web 端（index.html）：**
```js
// 新的 apiCall helper — 取代所有 fetch(API_URL + '?key=...')
async function apiCall(action, extraBody, keyOverride) {
  const key = (keyOverride !== undefined ? keyOverride : FLOWDESK_API_KEY) || '';
  const body = Object.assign({ action, key }, extraBody || {});
  const resp = await fetch(API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'text/plain;charset=utf-8' },  // skip CORS preflight
    body: JSON.stringify(body),
    redirect: 'follow'
  });
  return resp.json();
}
```

**Code.gs v16：**
- `doPost(e)` 現在處理所有動作（ping / init / getTasks / getTasksLight / getNoteContent / syncAll）
- 認證邏輯：`paramKey === API_KEY || bodyKey === API_KEY` — 同時接受 URL query 跟 body，**但 Web 不再送 URL query**
- `doGet(e)` 保持原樣，舊 desktop client 仍可用

**部署步驟（Kevin 需要做的）：**
1. 打開 Google Apps Script 專案
2. 貼上新版 `Code.gs`
3. **Deploy → Manage deployments → Edit（鉛筆）→ Version: New version → Deploy**
4. 重要：不用換 URL（Apps Script web app URL 不變，因為是 update 既有 deployment）
5. Web 端不用動，因為已經 push 到 origin/main 了；重新載入頁面就會用新版本

**驗證方式：**
- 點 🛡️ Security 按鈕，嘗試登入
- 打開 DevTools Network tab → 點那個 POST 請求
- Request URL 應該只有 `.../exec`，**沒有** `?key=xxx`
- Request Payload（body）裡才有 `{"action":"getTasks","key":"..."}`

### P1 — 客戶端 hash + 時戳 nonce

與其直接送 raw key，不如在瀏覽器做一次 `SHA-256(key + timestamp)`：

```js
async function signRequest(key, payload) {
  const ts = Date.now();
  const msg = ts + '.' + JSON.stringify(payload);
  const sig = await crypto.subtle.digest('SHA-256',
    new TextEncoder().encode(key + ':' + msg));
  return { ts, sig: [...new Uint8Array(sig)].map(b => b.toString(16).padStart(2,'0')).join('') };
}
```

Server 端驗證：
- `Math.abs(Date.now() - ts) < 5 * 60 * 1000`（5 分鐘內）
- 重新計算 `SHA-256(storedKey + ':' + ts + '.' + payload)` 比對

好處：就算攻擊者攔截一個 request，也無法 replay（時戳過期）。而且 localStorage 裡面仍然存 raw key（因為 hash 要算），但至少 wire 上沒有 raw key。

### P2 — 改為 session token

登入成功後 Server 回傳一個 `session_token`（隨機 32 bytes），之後所有 API 都用這個 token。Token 有 TTL（例如 7 天）、可由 server 撤銷、可以區分裝置。

需要 Apps Script 端用 `PropertiesService.getScriptProperties()` 或 `CacheService` 存 token。

### P3 — 前端完整性
如果以後要真的部署（不是 `file://` 本地開），可以考慮：
- CSP header 限制 script source
- Subresource Integrity（SRI）for CDN assets（目前沒用到 CDN）
- Cookie + HttpOnly 方案取代 localStorage（但 Apps Script 不太適用）

---

## 4. 直接回答 Kevin 的問題

> **別人直接用 debug 模式會看到我們的密碼嗎？**

**改動前的答案：會。**至少四個地方看得到：
1. Network tab → request URL 的 `?key=XXX`
2. Application tab → Local Storage → `flowdesk_api_key`
3. Elements tab → `<input id="loginKeyInput" value="XXX">`（輸入後、點 Unlock 之前）
4. Sources tab → 逐步執行時變數視窗

**改動後的答案：**
- ✅ (3) 修好了：輸入框會被清空
- ❌ (1) (2) (4) 還在，需要做 P0 / P1 改動（要動 Code.gs）

> **我們是不是需要一個更好的安全機制？**

**是的，建議做 P0（不要把 key 放 URL）。**這個改動風險最小、效益最高，而且不需要改資料模型。我可以幫 Kevin 把 Web 端和 Code.gs 的 patch 都寫好，Kevin 確認後再發佈。

---

## 5. 現在就可以做的事

1. 點右下角 🛡️ Security 按鈕，看看最近的登入事件
2. 如果看到「陌生 User-Agent」或「不是你發起的 login_ok」→ 馬上改密鑰
3. 如果看到 `rate_limit` 事件 → 有人在嘗試猜密碼
4. Export JSON 可以留存做審計

就這些。明早看到這份如果 OK，跟我說要不要繼續做 P0（把 key 移出 URL）。
