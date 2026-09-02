// Copyright (c) 2026, Ksolves India Limited and contributors
// Bulk "Push to Tally" action for the Supplier list view

frappe.listview_settings["Supplier"] = frappe.listview_settings["Supplier"] || {};

const tally_link_supplier_onload = frappe.listview_settings["Supplier"].onload;
frappe.listview_settings["Supplier"].onload = function (list_view) {
	if (tally_link_supplier_onload) {
		tally_link_supplier_onload(list_view);
	}

	list_view.page.add_actions_menu_item(__("Push to Tally"), () => {
		tally_link.bulk_push_to_tally({
			list_view,
			label: __("Push to Tally"),
			method: "tally_link.tally.api.push_supplier_to_tally",
			get_args: (doc) => ({ supplier_name: doc.name }),
		});
	});
};
