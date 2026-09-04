"""Seed system unit attributes (meter capabilities + structural attributes)."""

import frappe


def execute():
	from rental.rental.services.unit_type_service import ensure_system_unit_attributes
	ensure_system_unit_attributes()
