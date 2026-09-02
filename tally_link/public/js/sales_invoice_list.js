// Copyright (c) 2026, Ksolves India Limited and contributors
// Bulk "Push to Tally" action for the Sales Invoice list view

frappe.listview_settings["Sales Invoice"] = frappe.listview_settings["Sales Invoice"] || {};

const tally_link_sales_invoice_onload = frappe.listview_settings["Sales Invoice"].onload;
frappe.listview_settings["Sales Invoice"].onload = function (list_view) {
	if (tally_link_sales_invoice_onload) {
		tally_link_sales_invoice_onload(list_view);
	}

	list_view.page.add_actions_menu_item(__("Push to Tally"), () => {
		tally_link.bulk_push_to_tally({
			list_view,
			label: __("Push to Tally"),
			method: "tally_link.tally.api.push_sales_invoice_to_tally",
			get_args: (doc) => ({ sales_invoice_name: doc.name }),
		});
	});
};
