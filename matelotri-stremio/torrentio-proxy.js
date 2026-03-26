// Proxy local para Torrentio - evita bloqueo Cloudflare usando TLS fingerprint diferente
const http = require('http');
const https = require('https');
const tls = require('tls');

const PORT = 7001;

// Sobreescribir el cipher list para parecer un navegador real
const CIPHERS = [
    'TLS_AES_128_GCM_SHA256',
    'TLS_AES_256_GCM_SHA384',
    'TLS_CHACHA20_POLY1305_SHA256',
    'ECDHE-ECDSA-AES128-GCM-SHA256',
    'ECDHE-RSA-AES128-GCM-SHA256',
    'ECDHE-ECDSA-AES256-GCM-SHA384',
    'ECDHE-RSA-AES256-GCM-SHA384'
].join(':');

const server = http.createServer((req, res) => {
    // req.url viene como /path/to/resource
    const target = 'https://torrentio.strem.fun' + req.url;
    
    const options = {
        headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'es-ES,es;q=0.9',
            'Accept-Encoding': 'identity',
            'Connection': 'keep-alive',
            'Sec-Ch-Ua': '"Chromium";v="131", "Not_A Brand";v="24"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'none'
        },
        timeout: 20000,
        ciphers: CIPHERS,
        minVersion: 'TLSv1.2',
        maxVersion: 'TLSv1.3'
    };
    
    https.get(target, options, (proxyRes) => {
        // Seguir redirects
        if (proxyRes.statusCode >= 300 && proxyRes.statusCode < 400 && proxyRes.headers.location) {
            https.get(proxyRes.headers.location, options, (rRes) => {
                let d = '';
                rRes.on('data', c => d += c);
                rRes.on('end', () => {
                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(d);
                });
            }).on('error', () => { res.writeHead(502); res.end('{}'); });
            return;
        }
        
        let data = '';
        proxyRes.on('data', c => data += c);
        proxyRes.on('end', () => {
            res.writeHead(proxyRes.statusCode, { 'Content-Type': 'application/json' });
            res.end(data);
        });
    }).on('error', (e) => {
        res.writeHead(502);
        res.end(JSON.stringify({ error: e.message }));
    });
});

server.listen(PORT, '127.0.0.1', () => {
    console.log(`Torrentio proxy running on port ${PORT}`);
});
