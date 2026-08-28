import frappe
import os
import re


def get_context(context):
	context.csrf_token = frappe.sessions.get_csrf_token()

	index_path = os.path.join(
		os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
		"public", "frontend", "index.html"
	)

	scripts = []
	styles = []
	preloads = []

	if os.path.exists(index_path):
		with open(index_path, "r") as f:
			html = f.read()

		for match in re.finditer(r'<script[^>]*src="([^"]+)"[^>]*>', html):
			src = match.group(1)
			tag = match.group(0)
			is_module = "module" in tag
			scripts.append({"src": src, "module": is_module})

		for match in re.finditer(r'<link[^>]*rel="stylesheet"[^>]*href="([^"]+)"', html):
			styles.append(match.group(1))

		for match in re.finditer(r'<link[^>]*rel="modulepreload"[^>]*href="([^"]+)"', html):
			preloads.append(match.group(1))

	context.scripts = scripts
	context.styles = styles
	context.preloads = preloads
	context.no_cache = 1
	context.title = "Rental"

	return context
