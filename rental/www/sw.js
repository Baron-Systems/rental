/*
 * Service Worker — Rental PWA
 * Served at /sw.js via Frappe www/ renderer so it can control the root scope.
 * NOTE: rendered through Jinja — must not contain Jinja tag delimiters.
 */
var SW_VERSION = '1.0.0';
var SHELL_CACHE = 'rental-shell-' + SW_VERSION;
var ASSET_CACHE = 'rental-assets-' + SW_VERSION;
var APP_SHELL_URLS = ['/', '/frontend'];

self.addEventListener('install', function (event) {
	event.waitUntil(
		caches
			.open(SHELL_CACHE)
			.then(function (cache) {
				return cache.addAll(APP_SHELL_URLS);
			})
			.catch(function () {
				return null;
			})
			.then(function () {
				return self.skipWaiting();
			})
	);
});

self.addEventListener('activate', function (event) {
	event.waitUntil(
		caches
			.keys()
			.then(function (keys) {
				return Promise.all(
					keys
						.filter(function (key) {
							return (
								key.indexOf('rental-') === 0 &&
								key !== SHELL_CACHE &&
								key !== ASSET_CACHE
							);
						})
						.map(function (key) {
							return caches.delete(key);
						})
				);
			})
			.then(function () {
				return self.clients.claim();
			})
	);
});

self.addEventListener('message', function (event) {
	if (event.data && event.data.type === 'SKIP_WAITING') {
		self.skipWaiting();
	}
});

function networkFirst(request) {
	return fetch(request)
		.then(function (response) {
			if (response && response.ok) {
				var clone = response.clone();
				caches.open(SHELL_CACHE).then(function (cache) {
					cache.put(request, clone);
				});
			}
			return response;
		})
		.catch(function () {
			return caches.match(request).then(function (cached) {
				return cached || caches.match('/');
			});
		});
}

function cacheFirst(request) {
	return caches.match(request).then(function (cached) {
		if (cached) return cached;
		return fetch(request).then(function (response) {
			if (response && response.ok) {
				var clone = response.clone();
				caches.open(ASSET_CACHE).then(function (cache) {
					cache.put(request, clone);
				});
			}
			return response;
		});
	});
}

self.addEventListener('fetch', function (event) {
	var request = event.request;

	if (request.method !== 'GET') return;

	var url = new URL(request.url);
	if (url.origin !== self.location.origin) return;

	// Never intercept API calls, realtime socket or private files
	if (
		url.pathname.indexOf('/api/') === 0 ||
		url.pathname.indexOf('/socket.io') === 0 ||
		url.pathname.indexOf('/private/') === 0
	) {
		return;
	}

	if (request.mode === 'navigate') {
		event.respondWith(networkFirst(request));
		return;
	}

	if (url.pathname.indexOf('/assets/') === 0) {
		event.respondWith(cacheFirst(request));
	}
});
