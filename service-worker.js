const CACHE_NAME = 'ai-chatbot-v3';
const urlsToCache = [
  '/static/css/style.css',
  '/static/css/pricing.css',
  '/static/css/contrast-improvements.css',
  '/static/js/main.js',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png',
  '/static/manifest.json'
];

// Install event - cache resources
self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        console.log('Service Worker: Cache opened');
        return cache.addAll(urlsToCache);
      })
      .catch(function(error) {
        console.log('Service Worker: Cache failed', error);
      })
  );
});

// Fetch event - serve cached content when offline
self.addEventListener('fetch', function(event) {
  // Network-first strategy for HTML pages (navigation requests)
  if (event.request.mode === 'navigate' || 
      (event.request.method === 'GET' && event.request.headers.get('accept').includes('text/html'))) {
    event.respondWith(
      fetch(event.request)
        .catch(function() {
          // If network fails, try cache
          return caches.match('/offline.html') || 
                 new Response('Offline - Internetga ulanish yo\'q', {
                   status: 503,
                   statusText: 'Service Unavailable',
                   headers: new Headers({
                     'Content-Type': 'text/html'
                   })
                 });
        })
    );
    return;
  }

  // Cache-first strategy for static assets
  if (event.request.url.includes('/static/')) {
    event.respondWith(
      caches.match(event.request)
        .then(function(response) {
          if (response) {
            return response;
          }
          
          return fetch(event.request).then(function(response) {
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }
            
            var responseToCache = response.clone();
            caches.open(CACHE_NAME).then(function(cache) {
              cache.put(event.request, responseToCache);
            });
            
            return response;
          });
        })
    );
    return;
  }

  // Default: network-first for everything else
  event.respondWith(
    fetch(event.request)
      .catch(function() {
        return caches.match(event.request);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.map(function(cacheName) {
          if (cacheName !== CACHE_NAME) {
            console.log('Service Worker: Deleting old cache', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Push notification event
self.addEventListener('push', function(event) {
  if (event.data) {
    const data = event.data.json();
    const options = {
      body: data.body,
      icon: '/static/icons/icon-192x192.png',
      badge: '/static/icons/icon-72x72.png',
      vibrate: [100, 50, 100],
      data: {
        dateOfArrival: Date.now(),
        primaryKey: data.primaryKey
      }
    };
    
    event.waitUntil(
      self.registration.showNotification(data.title, options)
    );
  }
});

// Notification click event
self.addEventListener('notificationclick', function(event) {
  console.log('Notification click received');
  
  event.notification.close();
  
  event.waitUntil(
    clients.openWindow('/')
  );
});