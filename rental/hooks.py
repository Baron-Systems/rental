app_name = "rental"
app_title = "Rental"
app_publisher = "AL Baron Systems"
app_description = "Property and real estate rental management application"
app_email = "info@albaronsystems.com"
app_license = "mit"

# Apps
# ------------------

# Note: add_to_apps_screen and role_home_page conflict with www/frontend.html.
# The Vue SPA is accessible directly at /frontend and at / (via home_page hook).

# Website Route Rules
# -------------------
# Not used — causes 500 conflict with www/frontend.html.
# Vue uses hash-based routing (/#/login or /frontend#/login) instead.

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/rental/css/rental.css"
# app_include_js = "/assets/rental/js/rental.js"

# include js, css files in header of web template
# web_include_css = "/assets/rental/css/rental.css"
# web_include_js = "/assets/rental/js/rental.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "rental/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "rental/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# Serves the Vue SPA at / — www/frontend.html is rendered for the "frontend" route.
home_page = "frontend"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "rental.utils.jinja_methods",
# 	"filters": "rental.utils.jinja_filters"
# }

# Installation
# ------------

before_install = "rental.rental.install.before_install"
after_install = "rental.rental.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "rental.uninstall.before_uninstall"
# after_uninstall = "rental.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "rental.utils.before_app_install"
# after_app_install = "rental.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "rental.utils.before_app_uninstall"
# after_app_uninstall = "rental.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "rental.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "rental.notifications.get_notification_config"

# Permissions
# -----------
# Generic permission utilities for all account-scoped DocTypes

ACCOUNT_SCOPED_DOCTYPES = [
	"Rental Settings",
	"Rental Due Type",
	"Rental Building",
	"Rental Floor",
	"Rental Unit",
	"Rental Tenant",
	"Lease Contract",
	"Rental Due",
	"Rental Due Waiver",
	"Rental Receipt",
	"Rental Eviction",
	"Contract Cancellation Settlement",
	"Cancellation Settlement Item",
	"Unit Type",
	"Unit Attribute",
	"Unit Attribute Value",
]

permission_query_conditions = {
	dt: "rental.rental.utils.permissions.get_permission_query_conditions"
	for dt in ACCOUNT_SCOPED_DOCTYPES
}
# User Unit Preference needs a custom condition (rental_account + user, not just rental_account)
permission_query_conditions["User Unit Preference"] = "rental.rental.utils.permissions.get_permission_query_conditions"
# Rental Account uses owner_user (not rental_account field) for isolation
permission_query_conditions["Rental Account"] = "rental.rental.utils.permissions.get_permission_query_conditions"

has_permission = {
	dt: "rental.rental.utils.permissions.has_account_permission"
	for dt in ACCOUNT_SCOPED_DOCTYPES
}
has_permission["User Unit Preference"] = "rental.rental.utils.permissions.has_account_permission"
has_permission["Rental Account"] = "rental.rental.utils.permissions.has_account_permission"

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"rental.rental.tasks.daily.expire_contracts_task",
	],
}

# Testing
# -------

# before_tests = "rental.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "rental.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "rental.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "rental.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["rental.utils.before_request"]
# after_request = ["rental.utils.after_request"]

# Job Events
# ----------
# before_job = ["rental.utils.before_job"]
# after_job = ["rental.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"rental.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

