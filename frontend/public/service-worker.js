const CACHE_NAME = 'baobia-shell-v1'
const APP_SHELL = ['/', '/index.html', '/manifest.webmanifest', '/baobia-icon.svg']
const API_PREFIX = '/api/'
const STATIC_DESTINATIONS = new Set(['script', 'style', 'font', 'image'])

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(async (cache) => {
      const manifestResponse = await fetch('/precache-manifest.json')
      const manifest = await manifestResponse.json()
      await cache.addAll([...new Set([...APP_SHELL, ...manifest.assets])])
      await self.skipWaiting()
    }),
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((names) =>
        Promise.all(
          names
            .filter((name) => name.startsWith('baobia-shell-') && name !== CACHE_NAME)
            .map((name) => caches.delete(name)),
        ),
      )
      .then(() => self.clients.claim()),
  )
})

self.addEventListener('fetch', (event) => {
  const request = event.request
  const url = new URL(request.url)

  const isApiRequest = url.pathname === '/api' || url.pathname.startsWith(API_PREFIX)
  if (request.method !== 'GET' || url.origin !== self.location.origin || isApiRequest) {
    return
  }

  if (request.mode === 'navigate') {
    const cachePromise = caches.open(CACHE_NAME)
    const networkPromise = fetch(request).then((response) => {
      if (!response.ok) return response
      return cachePromise.then((cache) => cache.put(request, response.clone())).then(() => response)
    })
    event.waitUntil(networkPromise.then(() => undefined).catch(() => undefined))
    event.respondWith(
      networkPromise.catch(async () => (await caches.match(request)) || caches.match('/index.html')),
    )
    return
  }

  if (!STATIC_DESTINATIONS.has(request.destination) && !url.pathname.startsWith('/assets/')) return

  event.respondWith(
    caches.open(CACHE_NAME).then(async (cache) => {
      const cached = await cache.match(request, { ignoreVary: true })
      if (cached) return cached

      const response = await fetch(request)
      if (response.ok && response.type === 'basic') {
        await cache.put(request, response.clone())
      }
      return response
    }),
  )
})
