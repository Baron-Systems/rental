"""Seed default unit type ↔ attribute mappings."""

import frappe


def execute():
	from rental.rental.services.unit_type_service import seed_default_type_attributes
	seed_default_type_attributes()
