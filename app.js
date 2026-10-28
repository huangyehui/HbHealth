// 广州天气 & 心情记录 - 前端逻辑 (纯静态, 只读 CSV, 不做任何写入)
// 心情: data/mood_YYYY-MM-DD.csv      由 init_mood_files.py 预生成
// 天气: weather/gz_weather_YYYY-MM-DD.csv  只读的逐小时数据, 文件不存在则该区块不展示

const DATA_DIR = "data";        // 心情记录
const WEATHER_DIR = "weather";  // 天气逐小时数据
const DEFAULT_REPO = "huangyehui/HbHealth";
const DEFAULT_BRANCH = "master";
let moodRows = [];     // 当前日期的心情记录 [{datetime, mood, note}]
let currentDate = "";

const $ = (id) => document.getElementById(id);

// --- 本地日期/时间 (按当前系统时间, 而非 UTC) ---
const pad2 = (n) => String(n).padStart(2, "0");

function todayLocal() {
  const d = new Date();
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}

function nowLocalInput() {
  const d = new Date();
  return `${todayLocal()}T${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`;
}

function setVisible(id, visible) {
  const el = $(id);
  if (el) el.hidden = !visible;
}

// --- CSV 解析 (支持逗号, 双引号转义) ---
function parseCSV(text) {
  const lines = text.replace(/^\uFEFF/, "").split(/\r?\n/).filter((l) => l.length);
  if (!lines.length) return [];
  const header = splitLine(lines[0]);
  return lines.slice(1).map((line) => {
    const cells = splitLine(line);
    const obj = {};
    header.forEach((h, i) => (obj[h] = cells[i] ?? ""));
    return obj;
  });
}

function splitLine(line) {
  const out = [];
  let cur = "", inQ = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (inQ) {
      if (c === '"' && line[i + 1] === '"') { cur += '"'; i++; }
      else if (c === '"') inQ = false;
      else cur += c;
    } else {
      if (c === '"') inQ = true;
      else if (c === ",") { out.push(cur); cur = ""; }
      else cur += c;
    }
  }
  out.push(cur);
  return out;
}

function toCSV(rows, fields) {
  const esc = (v) => {
    v = (v ?? "").toString();
    return /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v;
  };
  const head = fields.join(",");
  const body = rows.map((r) => fields.map((f) => esc(r[f])).join(",")).join("\n");
  return "\uFEFF" + head + "\n" + body + "\n";
}

// 文件不存在返回 null, 由调用方决定是否展示
async function fetchCSV(path) {
  const res = await fetch(path, { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(res.status);
  return parseCSV(await res.text());
}

// --- 天气渲染 ---
async function loadWeather(date) {
  const rows = await fetchCSV(`${WEATHER_DIR}/gz_weather_${date}.csv`).catch(() => null);
  if (!rows || !rows.length) { setVisible("weatherCard", false); return; }
  const cols = ["time", "temperature_2m", "relative_humidity_2m", "precipitation", "pressure_msl", "weather"];
  const labels = { time: "时间", temperature_2m: "气温℃", relative_humidity_2m: "湿度%", precipitation: "降水mm", pressure_msl: "气压hPa", weather: "天气" };
  $("weatherBox").innerHTML = renderTable(rows, cols, labels);
  setVisible("weatherCard", true);
}

function renderTable(rows, cols, labels) {
  const head = cols.map((c) => `<th>${labels[c] || c}</th>`).join("");
  const body = rows.map((r) => "<tr>" + cols.map((c) => `<td>${r[c] ?? ""}</td>`).join("") + "</tr>").join("");
  return `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

// --- 心情渲染与编辑 ---
async function loadMood(date) {
  // 文件不存在(null) 则不展示表格区, 录入表单仍保留
  const rows = await fetchCSV(`${DATA_DIR}/mood_${date}.csv`).catch(() => null);
  setVisible("moodBox", rows !== null);
  moodRows = rows || [];
  renderMood();
}

function renderMood() {
  const box = $("moodBox");
  if (!moodRows.length) { box.innerHTML = '<span class="muted">暂无记录,添加一条吧</span>'; return; }
  const rowsHtml = moodRows.map((r, i) => `
    <tr>
      <td>${r.datetime || ""}</td>
      <td><span class="mood-tag">${r.mood || ""}</span></td>
      <td>${r.note || ""}</td>
      <td class="actions"><button class="ghost" data-del="${i}">删除</button></td>
    </tr>`).join("");
  box.innerHTML = `<table><thead><tr><th>时间</th><th>心情</th><th>备注</th><th></th></tr></thead><tbody>${rowsHtml}</tbody></table>`;
  box.querySelectorAll("[data-del]").forEach((b) =>
    b.addEventListener("click", () => { moodRows.splice(+b.dataset.del, 1); renderMood(); }));
}

function addMood() {
  const t = $("moodTime").value;
  const mood = $("moodState").value.trim();
  if (!t || !mood) { alert("请填写时间和心情状态"); return; }
  const datetime = t.replace("T", " ").padEnd(19, ":00").slice(0, 19);
  moodRows.push({ datetime, mood, note: $("moodNote").value.trim() });
  moodRows.sort((a, b) => a.datetime.localeCompare(b.datetime));
  $("moodState").value = ""; $("moodNote").value = "";
  renderMood();
}

// --- GitHub 配置 (存 localStorage) ---
function loadCfg() {
  $("ghRepo").value = localStorage.getItem("gh_repo") || DEFAULT_REPO;
  $("ghBranch").value = localStorage.getItem("gh_branch") || DEFAULT_BRANCH;
  $("ghToken").value = localStorage.getItem("gh_token") || "";
}

function saveCfg() {
  localStorage.setItem("gh_repo", $("ghRepo").value.trim());
  localStorage.setItem("gh_branch", $("ghBranch").value.trim() || DEFAULT_BRANCH);
  localStorage.setItem("gh_token", $("ghToken").value.trim());
  $("saveStatus").textContent = "配置已保存到本浏览器";
}

// base64 编码 UTF-8 字符串
function b64encode(str) {
  const bytes = new TextEncoder().encode(str);
  let bin = "";
  bytes.forEach((b) => (bin += String.fromCharCode(b)));
  return btoa(bin);
}

async function saveToGitHub() {
  const repo = $("ghRepo").value.trim() || DEFAULT_REPO;
  const branch = $("ghBranch").value.trim() || DEFAULT_BRANCH;
  const token = $("ghToken").value.trim();
  if (!repo || !token) { alert("请先填写仓库 owner/repo 和 Token"); return; }
  if (!currentDate) { alert("请先选择日期"); return; }

  const path = `${DATA_DIR}/mood_${currentDate}.csv`;
  const url = `https://api.github.com/repos/${repo}/contents/${path}`;
  const headers = { Authorization: `Bearer ${token}`, Accept: "application/vnd.github+json" };
  const status = $("saveStatus");
  status.textContent = "保存中…";

  try {
    // 取已有文件的 sha (若存在)
    let sha = undefined;
    const getRes = await fetch(`${url}?ref=${branch}`, { headers, cache: "no-store" });
    if (getRes.ok) sha = (await getRes.json()).sha;
    else if (getRes.status !== 404) throw new Error(`读取失败 ${getRes.status}`);

    const content = b64encode(toCSV(moodRows, ["datetime", "mood", "note"]));
    const body = {
      message: `update mood ${currentDate}`,
      content,
      branch,
      ...(sha ? { sha } : {}),
    };
    const putRes = await fetch(url, { method: "PUT", headers, body: JSON.stringify(body) });
    if (!putRes.ok) {
      const err = await putRes.json().catch(() => ({}));
      throw new Error(err.message || `提交失败 ${putRes.status}`);
    }
    status.textContent = `已保存到 ${repo} (${path})`;
  } catch (e) {
    status.textContent = "保存失败: " + e.message;
  }
}

function exportMood() {
  const csv = toCSV(moodRows, ["datetime", "mood", "note"]);
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `mood_${currentDate}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}

// --- 初始化 ---
async function load() {
  currentDate = $("datePicker").value;
  if (!currentDate) return;
  $("status").textContent = "加载中…";
  await Promise.all([loadWeather(currentDate), loadMood(currentDate)]);
  $("status").textContent = "已加载 " + currentDate;
}

function init() {
  $("datePicker").value = todayLocal();
  $("moodTime").value = nowLocalInput();
  loadCfg();
  $("loadBtn").addEventListener("click", load);
  $("addMoodBtn").addEventListener("click", addMood);
  $("exportBtn").addEventListener("click", exportMood);
  $("saveCfgBtn").addEventListener("click", saveCfg);
  $("saveGhBtn").addEventListener("click", saveToGitHub);
  load();
}

document.addEventListener("DOMContentLoaded", init);
