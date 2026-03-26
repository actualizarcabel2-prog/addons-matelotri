// ============================================================
// Matelotri Cinema — Stremio Addon Server v2.0
// Autenticación + Trial + Dashboard Admin + Gestión Usuarios
// ============================================================
const http = require("http");
const https = require("https");
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const PORT = 7000;
const DATA_DIR = path.join(__dirname, "data");
const USERS_FILE = path.join(DATA_DIR, "users.json");
const CONFIG_FILE = path.join(DATA_DIR, "config.json");

// ============================================================
// CONFIGURACIÓN
// ============================================================
const CONFIG = {
    // APIs
    TMDB_KEY: "f090bb54758cabf231fb605d3e3e0468",
    AD_KEY: "i5MI5R32vKVfOk3v46WA",
    
    // Admin
    ADMIN_USER: "admin",
    ADMIN_PASS: "cabel1n3",
    
    // Acceso addon
    ACCESS_PASS: "cabel1n3",
    
    // Trial
    TRIAL_DAYS: 30,  // 1 mes gratis
    
    // Branding
    NAME: "Matelotri Cinema",
    VERSION: "2.0.0",
    LOGO: "https://raw.githubusercontent.com/actualizarcabel2-prog/addons-matelotri/main/imagenes/matelotri_cinema_icon_1774476103177.png",
    BG: "https://raw.githubusercontent.com/actualizarcabel2-prog/addons-matelotri/main/imagenes/matelotri_cinema_fanart_1774476117417.png"
};

// ============================================================
// PERSISTENCIA
// ============================================================
if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });

function loadUsers() {
    try { return JSON.parse(fs.readFileSync(USERS_FILE, "utf-8")); }
    catch { return {}; }
}

function saveUsers(users) {
    fs.writeFileSync(USERS_FILE, JSON.stringify(users, null, 2));
}

function saveConfig() {
    fs.writeFileSync(CONFIG_FILE, JSON.stringify(CONFIG, null, 2));
}
saveConfig();

// ============================================================
// GESTIÓN USUARIOS
// ============================================================
function registerUser(deviceId, name = "") {
    const users = loadUsers();
    if (!users[deviceId]) {
        users[deviceId] = {
            id: deviceId,
            name: name || "Usuario-" + deviceId.slice(0, 6),
            created: new Date().toISOString(),
            lastSeen: new Date().toISOString(),
            active: true,
            premium: false,
            premiumExpires: null,
            trialUsed: false,
            trialStart: new Date().toISOString(),
            requests: 0
        };
        saveUsers(users);
    }
    return users[deviceId];
}

function checkAccess(deviceId) {
    const users = loadUsers();
    const user = users[deviceId];
    if (!user) return { allowed: false, reason: "no_user" };
    if (!user.active) return { allowed: false, reason: "disabled" };
    
    // Premium activo
    if (user.premium) {
        if (user.premiumExpires && new Date(user.premiumExpires) < new Date()) {
            user.premium = false;
            users[deviceId] = user;
            saveUsers(users);
        } else {
            return { allowed: true, type: "premium", user };
        }
    }
    
    // Trial
    const trialStart = new Date(user.trialStart);
    const now = new Date();
    const daysUsed = (now - trialStart) / (1000 * 60 * 60 * 24);
    if (daysUsed <= CONFIG.TRIAL_DAYS) {
        const daysLeft = Math.ceil(CONFIG.TRIAL_DAYS - daysUsed);
        return { allowed: true, type: "trial", daysLeft, user };
    }
    
    return { allowed: false, reason: "expired", user };
}

function updateLastSeen(deviceId) {
    const users = loadUsers();
    if (users[deviceId]) {
        users[deviceId].lastSeen = new Date().toISOString();
        users[deviceId].requests++;
        saveUsers(users);
    }
}

// ============================================================
// STREMIO MANIFEST
// ============================================================
function getManifest(deviceId) {
    return {
        id: "com.matelotri.cinema",
        version: CONFIG.VERSION,
        name: CONFIG.NAME,
        description: "Tu cine en casa — Películas, Series, Anime en 4K y 1080p",
        logo: CONFIG.LOGO,
        background: CONFIG.BG,
        catalogs: [
            { type: "movie", id: "matelotri-populares", name: "🎬 Populares", extra: [{ name: "skip" }] },
            { type: "movie", id: "matelotri-estrenos", name: "🆕 Estrenos", extra: [{ name: "skip" }] },
            { type: "movie", id: "matelotri-top", name: "⭐ Mejor Valoradas", extra: [{ name: "skip" }] },
            { type: "series", id: "matelotri-series", name: "📺 Series", extra: [{ name: "skip" }] },
            { type: "movie", id: "matelotri-buscar", name: "🔍 Buscar", extra: [{ name: "search", isRequired: true }] },
            { type: "series", id: "matelotri-buscar-series", name: "🔍 Buscar Series", extra: [{ name: "search", isRequired: true }] },
        ],
        resources: ["catalog", "stream"],
        types: ["movie", "series"],
        idPrefixes: ["tt"]
    };
}

// ============================================================
// HTTP HELPERS
// ============================================================
function fetchJSON(url) {
    return new Promise((resolve) => {
        const mod = url.startsWith("https") ? https : http;
        const req = mod.get(url, { headers: { "User-Agent": "MatelotriCinema/2.0" }, timeout: 6000 }, (res) => {
            let data = "";
            res.on("data", c => data += c);
            res.on("end", () => { try { resolve(JSON.parse(data)); } catch { resolve({}); } });
        });
        req.on("error", () => resolve({}));
        req.on("timeout", () => { req.destroy(); resolve({}); });
    });
}

// ============================================================
// TMDB
// ============================================================
async function tmdbGet(p, params = {}) {
    params.api_key = CONFIG.TMDB_KEY;
    params.language = "es-ES";
    const qs = Object.entries(params).map(([k,v]) => `${k}=${encodeURIComponent(v)}`).join("&");
    return fetchJSON(`https://api.themoviedb.org/3/${p}?${qs}`);
}

async function toMetas(results, type) {
    const metas = [];
    for (const item of (results || []).slice(0, 20)) {
        const title = item.title || item.name || "";
        const year = (item.release_date || item.first_air_date || "").slice(0, 4);
        let imdbId = item.imdb_id;
        if (!imdbId && item.id) {
            const ep = type === "movie" ? `movie/${item.id}` : `tv/${item.id}/external_ids`;
            const d = await tmdbGet(ep);
            imdbId = d.imdb_id;
        }
        if (!imdbId) continue;
        metas.push({
            id: imdbId, type, name: title,
            poster: item.poster_path ? `https://image.tmdb.org/t/p/w500${item.poster_path}` : "",
            background: item.backdrop_path ? `https://image.tmdb.org/t/p/w1280${item.backdrop_path}` : "",
            description: item.overview || "", year,
            imdbRating: item.vote_average ? item.vote_average.toFixed(1) : ""
        });
    }
    return metas;
}

async function handleCatalog(type, id, extra) {
    let data;
    const skip = extra.skip ? Math.floor(parseInt(extra.skip) / 20) + 1 : 1;
    if (id === "matelotri-populares") data = await tmdbGet("movie/popular", { page: skip });
    else if (id === "matelotri-estrenos") data = await tmdbGet("movie/now_playing", { page: skip });
    else if (id === "matelotri-top") data = await tmdbGet("movie/top_rated", { page: skip });
    else if (id === "matelotri-series") data = await tmdbGet("tv/popular", { page: skip });
    else if (id.includes("buscar") && extra.search) {
        const st = type === "series" ? "tv" : "movie";
        data = await tmdbGet(`search/${st}`, { query: extra.search, page: skip });
    }
    return { metas: await toMetas(data?.results || [], type) };
}

async function handleStream(type, id) {
    const url = `https://torrentio.strem.fun/alldebrid=${CONFIG.AD_KEY}/stream/${type}/${id}.json`;
    const data = await fetchJSON(url);
    return { streams: (data.streams || []).map(s => ({ ...s, name: s.name ? `🎬 ${s.name}` : CONFIG.NAME })) };
}

// ============================================================
// ADMIN DASHBOARD HTML
// ============================================================
function dashboardHTML(users) {
    const userList = Object.values(users);
    const active = userList.filter(u => u.active).length;
    const premium = userList.filter(u => u.premium).length;
    const trial = userList.filter(u => !u.premium && u.active).length;
    const totalReqs = userList.reduce((s, u) => s + (u.requests || 0), 0);
    
    // Agrupar por mes de registro
    const monthGroups = {};
    for (const u of userList) {
        const d = new Date(u.created);
        const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
        const label = d.toLocaleDateString('es-ES', { year: 'numeric', month: 'long' });
        if (!monthGroups[key]) monthGroups[key] = { label, users: [] };
        monthGroups[key].users.push(u);
    }
    
    // Generar secciones mensuales
    let monthSections = "";
    const sortedMonths = Object.keys(monthGroups).sort().reverse();
    for (const key of sortedMonths) {
        const g = monthGroups[key];
        let rows = "";
        for (const u of g.users.sort((a, b) => new Date(b.lastSeen) - new Date(a.lastSeen))) {
            const status = !u.active ? "🔴 Off" : u.premium ? "💎 Premium" : "🟢 Trial";
            const statusClass = !u.active ? "st-off" : u.premium ? "st-prem" : "st-trial";
            const trialDays = Math.max(0, CONFIG.TRIAL_DAYS - Math.floor((Date.now() - new Date(u.trialStart)) / 86400000));
            const expires = u.premium && u.premiumExpires ? new Date(u.premiumExpires).toLocaleDateString('es-ES') : "-";
            const created = new Date(u.created).toLocaleDateString('es-ES');
            const lastSeen = new Date(u.lastSeen).toLocaleString('es-ES');
            const phone = u.phone || "";
            const pass = u.generatedPass || "-";
            rows += `<tr>
                <td><b>${u.name}</b><br><small style="color:#666">${u.id.slice(0,8)}</small></td>
                <td><span class="${statusClass}">${status}</span></td>
                <td>${phone || '<span style="color:#555">-</span>'}</td>
                <td>${pass}</td>
                <td>${created}</td>
                <td>${trialDays}d</td>
                <td>${expires}</td>
                <td>${u.requests}</td>
                <td><small>${lastSeen}</small></td>
                <td class="actions">
                    <button class="btn-sm ${u.active?'btn-red':'btn-green'}" onclick="toggleUser('${u.id}')">${u.active?'⏸':'▶'}</button>
                    <button class="btn-sm btn-gold" onclick="setPremium('${u.id}')">💎</button>
                    <button class="btn-sm btn-blue" onclick="editUser('${u.id}','${u.name}','${phone}')">✏️</button>
                    <button class="btn-sm btn-red" onclick="deleteUser('${u.id}','${u.name}')">🗑</button>
                </td></tr>`;
        }
        monthSections += `
        <div class="month-folder">
            <div class="month-header" onclick="this.parentElement.classList.toggle('open')">
                <span class="folder-icon">📁</span>
                <span class="month-title">${g.label.charAt(0).toUpperCase() + g.label.slice(1)}</span>
                <span class="month-count">${g.users.length} clientes</span>
                <span class="arrow">▼</span>
            </div>
            <div class="month-body">
                <table><thead><tr>
                    <th>Cliente</th><th>Estado</th><th>📱 Teléfono</th><th>🔑 Pass</th>
                    <th>📅 Registro</th><th>Trial</th><th>Expira</th><th>Reqs</th>
                    <th>Última vez</th><th>Acciones</th>
                </tr></thead><tbody>${rows}</tbody></table>
            </div>
        </div>`;
    }
    
    return `<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${CONFIG.NAME} — Admin</title><style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',sans-serif;background:#0a0a15;color:#e0e0e0;min-height:100vh}
.header{background:linear-gradient(135deg,#0d001a,#1a0033,#330066);padding:20px;text-align:center;border-bottom:2px solid #ffd700;position:sticky;top:0;z-index:100}
.header h1{color:#ffd700;font-size:1.6em;text-shadow:0 2px 10px rgba(255,215,0,.3)}
.header p{color:#999;margin-top:3px;font-size:.85em}
.container{max-width:1400px;margin:15px auto;padding:0 12px}
.stats{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:12px 0}
.stat{text-align:center;padding:14px 8px;background:linear-gradient(135deg,#16213e,#1a1a2e);border-radius:10px;border:1px solid #222}
.stat .num{font-size:1.8em;color:#ffd700;font-weight:bold}
.stat .label{color:#888;font-size:.75em;margin-top:3px}
.card{background:#12121f;border-radius:10px;padding:14px;margin:12px 0;border:1px solid #1e1e3a}
.card h3{color:#ffd700;margin-bottom:10px;font-size:1em}
.topbar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:10px 0}
.btn{display:inline-flex;align-items:center;gap:5px;padding:8px 16px;background:linear-gradient(135deg,#6200ea,#9c27b0);
color:white;border:none;border-radius:8px;cursor:pointer;font-size:.85em}
.btn:hover{box-shadow:0 4px 15px rgba(98,0,234,.4);transform:translateY(-1px);transition:.2s}
.btn-restart{background:linear-gradient(135deg,#c62828,#e53935)}
.btn-restart:hover{box-shadow:0 4px 15px rgba(198,40,40,.5)}
.url-box{background:#080810;border:1px solid #ffd700;border-radius:8px;padding:8px 12px;
font-family:monospace;font-size:.8em;color:#ffd700;word-break:break-all;flex:1}
.month-folder{background:#0e0e1a;border:1px solid #1a1a2e;border-radius:10px;margin:8px 0;overflow:hidden}
.month-header{display:flex;align-items:center;gap:10px;padding:12px 16px;cursor:pointer;background:linear-gradient(135deg,#12122a,#1a1a3a);transition:.2s}
.month-header:hover{background:linear-gradient(135deg,#1a1a3a,#25254a)}
.folder-icon{font-size:1.2em}
.month-title{flex:1;font-weight:600;color:#e0c050}
.month-count{color:#888;font-size:.8em;background:#1a1a2e;padding:3px 10px;border-radius:12px}
.arrow{color:#666;transition:transform .3s}
.month-folder.open .arrow{transform:rotate(180deg)}
.month-body{max-height:0;overflow:hidden;transition:max-height .4s ease}
.month-folder.open .month-body{max-height:2000px}
table{width:100%;border-collapse:collapse;font-size:.78em}
th{background:#15152a;color:#ffd700;padding:8px 6px;text-align:left;border-bottom:2px solid #333;position:sticky;top:0}
td{padding:6px;border-bottom:1px solid #151520}
tr:hover{background:rgba(255,215,0,.03)}
.btn-sm{padding:3px 8px;border:none;border-radius:5px;cursor:pointer;font-size:.7em;margin:1px}
.btn-red{background:#8b0000;color:white}.btn-green{background:#006400;color:white}
.btn-gold{background:#b8860b;color:white}.btn-blue{background:#1565c0;color:white}
.st-off{color:#ff4444}.st-prem{color:#ffd700}.st-trial{color:#4caf50}
.actions{white-space:nowrap}
.modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.7);z-index:200;align-items:center;justify-content:center}
.modal.show{display:flex}
.modal-box{background:#12121f;border:1px solid #333;border-radius:12px;padding:24px;max-width:400px;width:90%}
.modal-box h3{color:#ffd700;margin-bottom:15px}
.modal-box input{width:100%;padding:10px;margin:6px 0;background:#1a1a2e;border:1px solid #333;border-radius:8px;color:#e0e0e0;font-size:.9em}
.modal-box button{margin:4px;padding:8px 16px;border:none;border-radius:8px;cursor:pointer}
.status-dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:#4caf50;margin-right:5px;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
@media(max-width:768px){.stats{grid-template-columns:repeat(3,1fr)} table{font-size:.7em} .topbar{flex-direction:column}}
</style></head><body>
<div class="header">
<h1>🎬 ${CONFIG.NAME}</h1>
<p>Panel de Administración — v${CONFIG.VERSION} <span class="status-dot"></span>Online</p>
</div>
<div class="container">
<div class="stats">
<div class="stat"><div class="num">${userList.length}</div><div class="label">Total Clientes</div></div>
<div class="stat"><div class="num">${active}</div><div class="label">Activos</div></div>
<div class="stat"><div class="num">${premium}</div><div class="label">Premium</div></div>
<div class="stat"><div class="num">${trial}</div><div class="label">Trial</div></div>
<div class="stat"><div class="num">${totalReqs}</div><div class="label">Peticiones</div></div>
</div>
<div class="topbar">
<div class="url-box" id="addonUrl">Cargando...</div>
<button class="btn" onclick="copyUrl()">📋 Copiar</button>
<button class="btn btn-restart" onclick="restartCloud()">🔄 Reiniciar Nube</button>
<button class="btn" onclick="location.reload()">🔃 Refresh</button>
</div>
<div class="card">
<h3>📂 Clientes por mes de registro</h3>
${monthSections || '<p style="color:#666;padding:20px;text-align:center">No hay clientes registrados</p>'}
</div>
<div class="card">
<h3>⚙️ Servidor</h3>
<p>AllDebrid: <code>${CONFIG.AD_KEY.slice(0,8)}...</code> | TMDb: <code>${CONFIG.TMDB_KEY.slice(0,8)}...</code></p>
<p>Trial: ${CONFIG.TRIAL_DAYS} días | Acceso: <code>${CONFIG.ACCESS_PASS}</code> | Uptime: <span id="up">0</span> min</p>
</div>
</div>
<!-- Modal editar usuario -->
<div class="modal" id="editModal">
<div class="modal-box">
<h3>✏️ Editar Cliente</h3>
<input id="editName" placeholder="Nombre del cliente">
<input id="editPhone" placeholder="📱 Teléfono" type="tel">
<input id="editPass" placeholder="🔑 Contraseña generada" readonly>
<button class="btn" onclick="saveUser()">💾 Guardar</button>
<button class="btn btn-restart" onclick="closeModal()">✕ Cerrar</button>
<button class="btn btn-gold" onclick="generatePass()">🎲 Generar Pass</button>
</div>
</div>
<script>
const start=${Date.now()};let editingId="";
setInterval(()=>document.getElementById("up").textContent=Math.floor((Date.now()-start)/60000),10000);
document.getElementById("addonUrl").textContent=location.origin+"/${CONFIG.ACCESS_PASS}/manifest.json";
// Abrir todas las carpetas del mes actual
document.querySelectorAll('.month-folder').forEach((f,i)=>{if(i===0)f.classList.add('open')});
function copyUrl(){navigator.clipboard.writeText(document.getElementById("addonUrl").textContent).then(()=>alert("✅ URL copiada!"))}
function toggleUser(id){if(confirm("¿Cambiar estado de este cliente?")){fetch("/api/admin/toggle?id="+id+"&pass=${CONFIG.ADMIN_PASS}").then(()=>location.reload())}}
function setPremium(id){const d=prompt("Días premium (30/90/365):");if(d)fetch("/api/admin/premium?id="+id+"&days="+d+"&pass=${CONFIG.ADMIN_PASS}").then(()=>location.reload())}
function editUser(id,name,phone){editingId=id;document.getElementById("editName").value=name||"";document.getElementById("editPhone").value=phone||"";document.getElementById("editPass").value="";document.getElementById("editModal").classList.add("show")}
function closeModal(){document.getElementById("editModal").classList.remove("show")}
function generatePass(){document.getElementById("editPass").value="MC-"+Math.random().toString(36).slice(2,8).toUpperCase()}
function saveUser(){fetch("/api/admin/edit?id="+editingId+"&name="+encodeURIComponent(document.getElementById("editName").value)+"&phone="+encodeURIComponent(document.getElementById("editPhone").value)+"&pass="+document.getElementById("editPass").value+"&adminpass=${CONFIG.ADMIN_PASS}").then(()=>{closeModal();location.reload()})}
function deleteUser(id,name){if(confirm("🗑 ¿Eliminar a "+name+"? No se puede deshacer.")){fetch("/api/admin/delete?id="+id+"&pass=${CONFIG.ADMIN_PASS}").then(()=>location.reload())}}
function restartCloud(){if(confirm("⚠️ ¿Reiniciar el servidor? Los clientes perderán conexión brevemente.")){fetch("/api/admin/restart?pass=${CONFIG.ADMIN_PASS}").then(r=>r.json()).then(d=>{alert("🔄 "+d.message);setTimeout(()=>location.reload(),3000)})}}
</script></body></html>`;
}

function loginHTML() {
    return `<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${CONFIG.NAME} — Login</title><style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Segoe UI',sans-serif;background:#0a0a15;color:#e0e0e0;min-height:100vh;display:flex;align-items:center;justify-content:center}
.box{background:#12121f;padding:40px;border-radius:16px;border:1px solid #333;max-width:400px;width:90%;text-align:center}
h1{color:#ffd700;margin-bottom:20px}
input{width:100%;padding:12px;margin:8px 0;background:#1a1a2e;border:1px solid #333;border-radius:8px;color:#e0e0e0;font-size:1em}
button{width:100%;padding:12px;margin-top:15px;background:linear-gradient(135deg,#6200ea,#9c27b0);color:white;border:none;border-radius:8px;font-size:1em;cursor:pointer}
</style></head><body>
<div class="box"><h1>🎬 ${CONFIG.NAME}</h1><p style="color:#888;margin-bottom:20px">Panel Admin</p>
<form method="POST" action="/admin/login"><input name="user" placeholder="Usuario"><input name="pass" type="password" placeholder="Contraseña">
<button type="submit">Entrar</button></form></div></body></html>`;
}

// ============================================================
// SERVER
// ============================================================
let requestCount = 0;

const server = http.createServer(async (req, res) => {
    requestCount++;
    const url = new URL(req.url, `http://localhost:${PORT}`);
    const p = url.pathname;
    
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Methods", "GET, POST");
    
    // --- ADMIN ---
    if (p === "/admin" || p === "/admin/") {
        const pass = url.searchParams.get("pass");
        if (pass === CONFIG.ADMIN_PASS) {
            res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
            return res.end(dashboardHTML(loadUsers()));
        }
        res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
        return res.end(loginHTML());
    }
    
    if (p === "/admin/login" && req.method === "POST") {
        let body = "";
        req.on("data", c => body += c);
        req.on("end", () => {
            const params = new URLSearchParams(body);
            if (params.get("user") === CONFIG.ADMIN_USER && params.get("pass") === CONFIG.ADMIN_PASS) {
                res.writeHead(302, { Location: `/admin?pass=${CONFIG.ADMIN_PASS}` });
            } else {
                res.writeHead(302, { Location: "/admin" });
            }
            res.end();
        });
        return;
    }
    
    // --- API ADMIN ---
    if (p === "/api/admin/toggle") {
        if (url.searchParams.get("pass") !== CONFIG.ADMIN_PASS) return res.writeHead(403) && res.end();
        const users = loadUsers();
        const id = url.searchParams.get("id");
        if (users[id]) { users[id].active = !users[id].active; saveUsers(users); }
        res.writeHead(200, { "Content-Type": "application/json" });
        return res.end(JSON.stringify({ ok: true }));
    }
    
    if (p === "/api/admin/premium") {
        if (url.searchParams.get("pass") !== CONFIG.ADMIN_PASS) return res.writeHead(403) && res.end();
        const users = loadUsers();
        const id = url.searchParams.get("id");
        const days = parseInt(url.searchParams.get("days") || "30");
        if (users[id]) {
            users[id].premium = true;
            users[id].premiumExpires = new Date(Date.now() + days * 86400000).toISOString();
            saveUsers(users);
        }
        res.writeHead(200, { "Content-Type": "application/json" });
        return res.end(JSON.stringify({ ok: true }));
    }
    
    // Editar usuario (nombre, teléfono, contraseña)
    if (p === "/api/admin/edit") {
        if (url.searchParams.get("adminpass") !== CONFIG.ADMIN_PASS) return res.writeHead(403) && res.end();
        const users = loadUsers();
        const id = url.searchParams.get("id");
        if (users[id]) {
            const name = url.searchParams.get("name");
            const phone = url.searchParams.get("phone");
            const pass = url.searchParams.get("pass");
            if (name) users[id].name = name;
            if (phone) users[id].phone = phone;
            if (pass) users[id].generatedPass = pass;
            saveUsers(users);
        }
        res.writeHead(200, { "Content-Type": "application/json" });
        return res.end(JSON.stringify({ ok: true }));
    }
    
    // Eliminar usuario
    if (p === "/api/admin/delete") {
        if (url.searchParams.get("pass") !== CONFIG.ADMIN_PASS) return res.writeHead(403) && res.end();
        const users = loadUsers();
        const id = url.searchParams.get("id");
        if (users[id]) { delete users[id]; saveUsers(users); }
        res.writeHead(200, { "Content-Type": "application/json" });
        return res.end(JSON.stringify({ ok: true }));
    }
    
    // Reiniciar servidor
    if (p === "/api/admin/restart") {
        if (url.searchParams.get("pass") !== CONFIG.ADMIN_PASS) return res.writeHead(403) && res.end();
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ ok: true, message: "Servidor reiniciando..." }));
        setTimeout(() => { process.exit(0); }, 1000);
        return;
    }
    
    if (p === "/api/stats") {
        const users = loadUsers();
        res.writeHead(200, { "Content-Type": "application/json" });
        return res.end(JSON.stringify({ requests: requestCount, uptime: process.uptime(), users: Object.keys(users).length }));
    }
    
    // --- STREMIO ADDON (protegido con pass) ---
    const addonMatch = p.match(/^\/([^/]+)\/(.*)/);
    if (addonMatch) {
        const [, accessKey, rest] = addonMatch;
        
        // Verificar clave de acceso
        if (accessKey !== CONFIG.ACCESS_PASS) {
            res.writeHead(403, { "Content-Type": "application/json" });
            return res.end(JSON.stringify({ error: "Acceso denegado. Contraseña incorrecta." }));
        }
        
        // Device ID (hash del IP como identificador básico)
        const clientIP = req.headers["x-forwarded-for"] || req.socket.remoteAddress || "unknown";
        const deviceId = crypto.createHash("md5").update(clientIP).digest("hex").slice(0, 12);
        
        // Registrar usuario si es nuevo
        registerUser(deviceId);
        
        // Verificar acceso
        const access = checkAccess(deviceId);
        
        // Manifest
        if (rest === "manifest.json") {
            updateLastSeen(deviceId);
            if (!access.allowed) {
                const manifest = getManifest(deviceId);
                manifest.description = "⛔ Tu acceso ha expirado. Contacta con el admin.";
                manifest.catalogs = [];
                manifest.resources = [];
                res.writeHead(200, { "Content-Type": "application/json" });
                return res.end(JSON.stringify(manifest));
            }
            const manifest = getManifest(deviceId);
            if (access.type === "trial") {
                manifest.description = `✅ Trial: ${access.daysLeft} días restantes — ${CONFIG.NAME}`;
            } else {
                manifest.description = `💎 Premium — ${CONFIG.NAME}`;
            }
            res.writeHead(200, { "Content-Type": "application/json" });
            return res.end(JSON.stringify(manifest));
        }
        
        // Verificar acceso para catalog y stream
        if (!access.allowed) {
            res.writeHead(200, { "Content-Type": "application/json" });
            return res.end(JSON.stringify({ metas: [], streams: [] }));
        }
        
        updateLastSeen(deviceId);
        
        // Catalog
        const catMatch = rest.match(/^catalog\/(\w+)\/([^/]+)(?:\/([^/]+))?\.json/);
        if (catMatch) {
            const [, type, id, extraStr] = catMatch;
            const extra = {};
            if (extraStr) for (const pt of extraStr.split("&")) { const [k,v] = pt.split("="); extra[k] = decodeURIComponent(v); }
            const result = await handleCatalog(type, id, extra);
            res.writeHead(200, { "Content-Type": "application/json" });
            return res.end(JSON.stringify(result));
        }
        
        // Stream
        const strMatch = rest.match(/^stream\/(\w+)\/([^/]+)\.json/);
        if (strMatch) {
            const [, type, id] = strMatch;
            const result = await handleStream(type, id);
            res.writeHead(200, { "Content-Type": "application/json" });
            return res.end(JSON.stringify(result));
        }
    }
    
    // Root redirect
    if (p === "/" || p === "") {
        res.writeHead(302, { Location: "/admin" });
        return res.end();
    }
    
    res.writeHead(404, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ error: "Not found" }));
});

server.listen(PORT, () => {
    console.log(`\n🎬 ${CONFIG.NAME} v${CONFIG.VERSION}`);
    console.log(`   Servidor: http://localhost:${PORT}/`);
    console.log(`   Admin:    http://localhost:${PORT}/admin`);
    console.log(`   Addon:    http://localhost:${PORT}/${CONFIG.ACCESS_PASS}/manifest.json`);
    console.log(`   Pass:     ${CONFIG.ACCESS_PASS}\n`);
});
