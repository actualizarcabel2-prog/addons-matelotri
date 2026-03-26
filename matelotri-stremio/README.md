# 🎬 Matelotri Cinema — Stremio Addon

## Inicio rápido
```bash
node server.js
```
- **Dashboard**: http://localhost:7000/admin
- **Addon URL**: http://localhost:7000/cabel1n3/manifest.json

## Claves y APIs

| Servicio | Clave | Uso |
|---|---|---|
| **TMDb** | `f090bb54758cabf231fb605d3e3e0468` | Metadatos pelis/series |
| **AllDebrid** | `i5MI5R32vKVfOk3v46WA` | Resolución streams premium |
| **Admin user** | `admin` | Login dashboard |
| **Admin pass** | `cabel1n3` | Login dashboard + acceso addon |
| **DigitalOcean API** | `(ver CLAVES en PC local)` | VPS |
| **VPS IP** | `209.38.230.244` | Servidor producción |
| **Cloudflare** | `actualizarcabel3@gmail.com` / `cabel1n3` | Tunnel |
| **GitHub** | `actualizarcabel2-prog` | Repositorio |

## Estructura
```
matelotri-stremio/
├── server.js        # Servidor principal (addon + dashboard)
├── data/
│   ├── users.json   # Base de datos usuarios (auto-generado)
│   └── config.json  # Configuración activa (auto-generado)
├── worker.js        # Versión Cloudflare Workers (alternativa)
├── wrangler.toml    # Config Cloudflare Workers
└── README.md        # Este archivo
```

## Despliegue VPS
```bash
# Conectar
ssh -i ~/.ssh/suggy_do3 root@209.38.230.244

# Instalar
mkdir -p /root/matelotri-cinema
# copiar server.js
pm2 start server.js --name matelotri-cinema
pm2 save
```

## Protección
- Acceso addon requiere password en la URL: `/cabel1n3/manifest.json`
- Trial 30 días automático al primer acceso
- Panel admin protegido con login
- Usuarios se pueden desactivar/activar desde dashboard
