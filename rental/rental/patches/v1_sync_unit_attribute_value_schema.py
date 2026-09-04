"""
Patch: Sync Unit Attribute Value schema

Ensures the value_decimal column exists with the correct type.

Background:
    The value_decimal field was originally defined with fieldtype "Decimal",
    which Frappe does not recognize as a data fieldtype (it is absent from
    frappe.model.data_fieldtypes).  This caused the ORM to silently ignore
    the field — values set on the doc were never persisted to the database.

    The fieldtype was corrected to "Float" in the DocType JSON, but
    ``bench migrate`` only syncs the database schema when the DocType JSON
    file is detected as changed.  On sites where the DocField record was
    already updated (e.g. via a previous migrate run that synced the JSON
    but could not create the column because the fieldtype was still
    "Decimal"), the database column may be missing or have the wrong type.

    This patch forces a schema sync via ``frappe.db.updatedb`` so that the
    column is created or corrected regardless of the current database state.
"""

import frappe
from frappe.model.meta import Meta


def execute():
	"""Force-sync the Unit Attribute Value table schema."""
	doctype = "Unit Attribute Value"
	meta = Meta(frappe.get_meta(doctype))
	frappe.db.updatedb(doctype, meta)
	frappe.db.commit()
