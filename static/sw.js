const CACHE_NAME = 'gym-manager-v1';
const ASSETS = [
    '/',
    '/dashboard',
    '/add_member',
    '/fees',
    '/static/manifest.json',
    '/static/style.css',
    '/static/icon.png'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => cache.addAll(ASSETS))
    );
});

self.addEventListener('fetch', (event) => {
    event.respondWith(
        fetch(event.request).catch(() => {
            return caches.match(event.request);
        })
    );
});
