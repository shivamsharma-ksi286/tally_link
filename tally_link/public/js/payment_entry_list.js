// Copyright (c) 2026, Ksolves India Limited and contributors
// Bulk "Push to Tally" action for the Payment Entry list view

frappe.listview_settings["Payment Entry"] = frappe.listview_settings["Payment Entry"] || {};

const tally_link_payment_entry_onload = frappe.listview_settings["Payment Entry"].onload;
frappe.listview_settings["Payment Entry"].onload = function (list_view) {
	if (tally_link_payment_entry_onload) {
		tally_link_payment_entry_onload(list_view);
	}

	list_view.page.add_actions_menu_item(__("Push to Tally"), () => {
		tally_link.bulk_push_to_tally({
			list_view,
			label: __("Push to Tally"),
			method: "tally_link.tally.api.push_payment_entry_to_tally",
			get_args: (doc) => ({ payment_entry_name: doc.name }),
		});
	});
};
