import frappe, json

def execute():
    orphan_unit_names = [
        'UNT-00011','UNT-00012','UNT-00013','UNT-00014','UNT-00015',
        'UNT-00016','UNT-00017','UNT-00018','UNT-00019','UNT-00020',
        'UNT-00021','UNT-00022','UNT-00023','UNT-00024','UNT-00025',
        'UNT-00026','UNT-00027','UNT-00028','UNT-00029','UNT-00030',
    ]

    units = frappe.db.sql(
        "SELECT name, unit_number, rental_account, building, unit_type, "
        "rooms_count, bathrooms_count, "
        "electricity_meter_number, water_meter_number, "
        "current_electricity_meter_reading, current_water_meter_reading "
        "FROM `tabRental Unit` WHERE name IN %s",
        (tuple(orphan_unit_names),), as_dict=True,
    )

    accounts = frappe.db.sql(
        "SELECT name, is_active, account_name, owner_user "
        "FROM `tabRental Account` "
        "WHERE name IN (SELECT DISTINCT rental_account FROM `tabRental Unit` WHERE name IN %s)",
        (tuple(orphan_unit_names),), as_dict=True,
    )

    contracts = frappe.db.sql(
        "SELECT name, unit, status, start_date, end_date, is_archived, is_historical "
        "FROM `tabLease Contract` WHERE unit IN %s",
        (tuple(orphan_unit_names),), as_dict=True,
    )
    contract_names = [c['name'] for c in contracts]

    metered_charges = []
    if contract_names:
        metered_charges = frappe.db.sql(
            "SELECT cc.name, cc.parent, cc.due_type, cc.calculation_method, "
            "cc.opening_meter_reading, rdt.due_type_code, rdt.due_type_name "
            "FROM `tabContract Charge` cc "
            "LEFT JOIN `tabRental Due Type` rdt ON cc.due_type = rdt.name "
            "WHERE cc.parent IN %s AND cc.parenttype = 'Lease Contract'",
            (tuple(contract_names),), as_dict=True,
        )

    existing_attr_values = frappe.db.sql(
        "SELECT uav.name, uav.unit, uav.attribute, uav.value_check, "
        "ua.code, ua.capability_code "
        "FROM `tabUnit Attribute Value` uav "
        "LEFT JOIN `tabUnit Attribute` ua ON uav.attribute = ua.name "
        "WHERE uav.unit IN %s",
        (tuple(orphan_unit_names),), as_dict=True,
    )

    rooms_attr = frappe.db.get_value('Unit Attribute', {'code': 'rooms_count', 'is_system': 1}, 'name')
    bathrooms_attr = frappe.db.get_value('Unit Attribute', {'code': 'bathrooms_count', 'is_system': 1}, 'name')
    elec_attr = frappe.db.get_value('Unit Attribute', {'code': 'electricity_meter', 'is_system': 1}, 'name')
    water_attr = frappe.db.get_value('Unit Attribute', {'code': 'water_meter', 'is_system': 1}, 'name')

    result = {
        'units': units,
        'accounts_found': accounts,
        'contracts': contracts,
        'metered_charges': metered_charges,
        'existing_attr_values': existing_attr_values,
        'attr_names': {
            'rooms': rooms_attr,
            'bathrooms': bathrooms_attr,
            'elec': elec_attr,
            'water': water_attr,
        },
    }
    print(json.dumps(result, default=str, indent=2, ensure_ascii=False))
