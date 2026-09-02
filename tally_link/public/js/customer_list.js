// Copyright (c) 2026, Ksolves India Limited and contributors
// Bulk "Push to Tally" action for the Customer list view

frappe.listview_settings["Customer"] = frappe.listview_settings["Customer"] || {};

const tally_link_customer_onload = frappe.listview_settings["Customer"].onload;
frappe.listview_settings["Customer"].onload = function (list_view) {
	if (tally_link_customer_onload) {
		tally_link_customer_onload(list_view);
	}

	list_view.page.add_actions_menu_item(__("Push to Tally"), () => {
		tally_link.bulk_push_to_tally({
			list_view,
			label: __("Push to Tally"),
			method: "tally_link.tally.api.push_customer_to_tally",
			get_args: (doc) => ({ customer_name: doc.name }),
		});
	});
};
