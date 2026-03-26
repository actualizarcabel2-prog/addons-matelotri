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
    
    let rows = "";
    for (const u of userList.sort((a,b) => new Date(b.lastSeen) - new Date(a.lastSeen))) {
        const status = !u.active ? "🔴 Desactivado" : u.premium ? "💎 Premium" : "🟢 Trial";
        const expires = u.premium && u.premiumExpires ? new Date(u.premiumExpires).toLocaleDateString() : "-";
        const trialDays = Math.max(0, CONFIG.TRIAL_DAYS - Math.floor((Date.now() - new Date(u.trialStart)) / 86400000));
        rows += `<tr>
            <td>${u.name}</td><td>${u.id.slice(0,10)}...</td>
            <td>${status}</td><td>${trialDays}d</td><td>${expires}</td>
            <td>${u.requests}</td><td>${new Date(u.lastSeen).toLocaleString()}</td>
            <td>
                <button class="btn-sm ${u.active?'btn-red':'btn-green'}" onclick="toggleUser('${u.id}')">${u.active?'Desactivar':'Activar'}</button>
                <button class="btn-sm btn-gold" onclick="setPremium('${u.id}')">Premium</button>
            </td></tr>`;
    }
    
    return `<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${CONFIG.NAME} — Admin</title><style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',sans-serif;background:#0a0a15;color:#e0e0e0;min-height:100vh}
.header{background:linear-gradient(135deg,#0d001a,#1a0033,#330066);padding:25px;text-align:center;border-bottom:2px solid #ffd700}
.header h1{color:#ffd700;font-size:1.8em;text-shadow:0 2px 10px rgba(255,215,0,.3)}
.header p{color:#999;margin-top:4px;font-size:.9em}
.container{max-width:1100px;margin:20px auto;padding:0 15px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:15px 0}
.stat{text-align:center;padding:18px;background:linear-gradient(135deg,#16213e,#1a1a2e);border-radius:12px;border:1px solid #222}
.stat .num{font-size:2.2em;color:#ffd700;font-weight:bold}
.stat .label{color:#888;font-size:.8em;margin-top:4px}
.card{background:#12121f;border-radius:12px;padding:18px;margin:15px 0;border:1px solid #1e1e3a}
.card h3{color:#ffd700;margin-bottom:12px;font-size:1.1em}
table{width:100%;border-collapse:collapse;font-size:.85em}
th{background:#1a1a2e;color:#ffd700;padding:10px 8px;text-align:left;border-bottom:2px solid #333}
td{padding:8px;border-bottom:1px solid #1a1a2a}
tr:hover{background:#1a1a2e}
.btn-sm{padding:4px 10px;border:none;border-radius:6px;cursor:pointer;font-size:.75em;margin:2px}
.btn-red{background:#8b0000;color:white}.btn-green{background:#006400;color:white}
.btn-gold{background:#b8860b;color:white}
.btn{display:inline-block;padding:10px 20px;background:linear-gradient(135deg,#6200ea,#9c27b0);
color:white;border:none;border-radius:8px;cursor:pointer;font-size:.95em;margin:5px}
.btn:hover{box-shadow:0 4px 15px rgba(98,0,234,.4)}
.url-box{background:#080810;border:1px solid #ffd700;border-radius:8px;padding:10px;
font-family:monospace;font-size:.85em;color:#ffd700;word-break:break-all;margin:8px 0}
.login-box{max-width:400px;margin:80px auto;text-align:center}
.login-box input{width:100%;padding:12px;margin:8px 0;background:#1a1a2e;border:1px solid #333;
border-radius:8px;color:#e0e0e0;font-size:1em}
@media(max-width:768px){.stats{grid-template-columns:repeat(2,1fr)} table{font-size:.75em}}
</style></head><body>
<div class="header">
<h1>🎬 ${CONFIG.NAME}</h1>
<p>Panel de Administración — v${CONFIG.VERSION}</p>
</div>
<div class="container">
<div class="stats">
<div class="stat"><div class="num">${userList.length}</div><div class="label">Total Usuarios</div></div>
<div class="stat"><div class="num">${active}</div><div class="label">Activos</div></div>
<div class="stat"><div class="num">${premium}</div><div class="label">Premium</div></div>
<div class="stat"><div class="num">${trial}</div><div class="label">Trial</div></div>
</div>
<div class="card">
<h3>🔗 URL del Addon (para Stremio)</h3>
<div class="url-box" id="addonUrl">Cargando...</div>
<button class="btn" onclick="copyUrl()">📋 Copiar</button>
</div>
<div class="card">
<h3>👥 Usuarios</h3>
<table><thead><tr><th>Nombre</th><th>ID</th><th>Estado</th><th>Trial</th><th>Expira</th><th>Reqs</th><th>Última vez</th><th>Acciones</th></tr></thead>
<tbody>${rows}</tbody></table>
</div>
<div class="card">
<h3>⚙️ Configuración</h3>
<p>AllDebrid: <code>${CONFIG.AD_KEY.slice(0,8)}...</code> | TMDb: <code>${CONFIG.TMDB_KEY.slice(0,8)}...</code></p>
<p>Trial: ${CONFIG.TRIAL_DAYS} días | Pass acceso: <code>${CONFIG.ACCESS_PASS}</code></p>
<p>Uptime: <span id="up">0</span> min</p>
</div>
</div>
<script>
const start=${Date.now()};
setInterval(()=>document.getElementById("up").textContent=Math.floor((Date.now()-start)/60000),10000);
document.getElementById("addonUrl").textContent=location.origin+"/${CONFIG.ACCESS_PASS}/manifest.json";
function copyUrl(){navigator.clipboard.writeText(document.getElementById("addonUrl").textContent).then(()=>alert("Copiado!"))}
function toggleUser(id){fetch("/api/admin/toggle?id="+id+"&pass=${CONFIG.ADMIN_PASS}").then(()=>location.reload())}
function setPremium(id){const d=prompt("Días premium (30/90/365):");if(d)fetch("/api/admin/premium?id="+id+"&days="+d+"&pass=${CONFIG.ADMIN_PASS}").then(()=>location.reload())}
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
