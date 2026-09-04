"""Seed system unit types (8 types: apartment, shop, office, etc.)."""

import frappe


def execute():
	from rental.rental.services.unit_type_service import ensure_system_unit_types
	ensure_system_unit_types()
