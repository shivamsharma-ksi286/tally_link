// Copyright (c) 2026, Ksolves India Limited and contributors
// Shared helper: bulk-push selected list view records to Tally, one at a
// time, reusing the existing single-record "Push to Tally" whitelisted
// methods so the push logic stays in one place.

frappe.provide("tally_link");

tally_link.bulk_push_to_tally = function ({ list_view, label, method, get_args }) {
	const selected = list_view.get_checked_items();

	if (!selected.length) {
		frappe.msgprint(__("Select at least one record to push to Tally."));
		return;
	}

	frappe.confirm(__("Push {0} selected record(s) to Tally?", [selected.length]), () => {
		tally_link._run_bulk_push(list_view, selected, label, method, get_args);
	});
};

tally_link._run_bulk_push = async function (list_view, selected, label, method, get_args) {
	const total = selected.length;
	const pushed = [];
	const failed = [];

	for (let i = 0; i < total; i++) {
		const doc = selected[i];
		frappe.show_progress(label, i, total, __("Pushing {0} ({1} of {2})...", [doc.name, i + 1, total]));

		let result;
		try {
			result = await frappe.xcall(method, get_args(doc));
		} catch (e) {
			result = { success: false, message: (e && e.message) || String(e) };
		}

		if (result && result.success) {
			pushed.push(doc.name);
		} else {
			failed.push({
				name: doc.name,
				message: (result && result.message) || __("Unknown error. Check Error Log."),
			});
		}
	}

	frappe.show_progress(label, total, total, __("Done"), true);
	list_view.clear_checked_items();
	list_view.refresh();

	let html = `<p>${__("Pushed {0} of {1} record(s) to Tally successfully.", [pushed.length, total])}</p>`;
	if (failed.length) {
		const rows = failed
			.map(
				(f) =>
					`<li><strong>${frappe.utils.escape_html(f.name)}</strong>: ${frappe.utils.escape_html(f.message)}</li>`
			)
			.join("");
		html += `<p>${__("Failed ({0}):", [failed.length])}</p><ul>${rows}</ul>`;
	}

	frappe.msgprint({
		title: label,
		message: html,
		indicator: failed.length ? (pushed.length ? "orange" : "red") : "green",
	});
};
