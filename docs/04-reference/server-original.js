const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 3000;
const PUBLIC_DIR = __dirname;

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.txt': 'text/plain; charset=utf-8',
  '.cfg': 'text/plain; charset=utf-8',
  '.csv': 'text/csv; charset=utf-8'
};

// Connected live-reload clients
const clients = new Set();

function broadcastReload() {
  console.log(`[LiveReload] Detected file change -> Notifying ${clients.size} client(s) to reload...`);
  for (const res of clients) {
    try {
      res.write(`data: reload\n\n`);
    } catch (e) {
      clients.delete(res);
    }
  }
}

// Watch directory for changes with debouncing
let debounceTimer = null;
try {
  fs.watch(PUBLIC_DIR, { recursive: true }, (eventType, filename) => {
    if (!filename) return;
    // Ignore internal or git/node files
    if (filename.includes('.git') || filename.includes('node_modules') || filename.endsWith('.log')) return;
    
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      broadcastReload();
    }, 120);
  });
  console.log('[LiveReload] File watcher initialized on directory:', PUBLIC_DIR);
} catch (e) {
  console.error('[LiveReload] Could not start watcher:', e.message);
}

const server = http.createServer((req, res) => {
  let reqUrl = req.url.split('?')[0];

  // 1. Live reload SSE endpoint
  if (reqUrl === '/live-reload') {
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      'Connection': 'keep-alive',
      'Access-Control-Allow-Origin': '*'
    });
    res.write('data: connected\n\n');
    clients.add(res);
    req.on('close', () => {
      clients.delete(res);
    });
    return;
  }

  // 2. Default to mockup.html for root path '/' or '/index.html'
  if (reqUrl === '/' || reqUrl === '' || reqUrl === '/index.html') {
    reqUrl = '/mockup.html';
  }

  const safePath = path.normalize(reqUrl).replace(/^(\.\.[\/\\])+/, '');
  const filePath = path.join(PUBLIC_DIR, safePath);

  fs.stat(filePath, (err, stats) => {
    if (err || !stats.isFile()) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end('404 Not Found');
      return;
    }

    const ext = path.extname(filePath).toLowerCase();
    const contentType = MIME_TYPES[ext] || 'application/octet-stream';

    // Strict no-cache headers so browser always sees newest updates
    res.writeHead(200, {
      'Content-Type': contentType,
      'Cache-Control': 'no-cache, no-store, must-revalidate, max-age=0',
      'Pragma': 'no-cache',
      'Expires': '0'
    });

    const readStream = fs.createReadStream(filePath);
    readStream.pipe(res);
  });
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`=======================================================`);
  console.log(` Network Backup Dashboard server is running!`);
  console.log(` URL: http://localhost:${PORT}`);
  console.log(` Serving file: mockup.html by default`);
  console.log(` Live-reload is active!`);
  console.log(`=======================================================`);
});
