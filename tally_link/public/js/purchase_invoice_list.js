// Copyright (c) 2026, Ksolves India Limited and contributors
// Bulk "Push to Tally" action for the Purchase Invoice list view

frappe.listview_settings["Purchase Invoice"] = frappe.listview_settings["Purchase Invoice"] || {};

const tally_link_purchase_invoice_onload = frappe.listview_settings["Purchase Invoice"].onload;
frappe.listview_settings["Purchase Invoice"].onload = function (list_view) {
	if (tally_link_purchase_invoice_onload) {
		tally_link_purchase_invoice_onload(list_view);
	}

	list_view.page.add_actions_menu_item(__("Push to Tally"), () => {
		tally_link.bulk_push_to_tally({
			list_view,
			label: __("Push to Tally"),
			method: "tally_link.tally.api.push_purchase_invoice_to_tally",
			get_args: (doc) => ({ purchase_invoice_name: doc.name }),
		});
	});
};
