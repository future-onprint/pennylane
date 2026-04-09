const SYNC_STATUS_COLOR = {
	Synced: "green",
	Pending: "orange",
	Failed: "red",
	Deleted: "purple",
};

frappe.listview_settings["Pennylane Customer Invoice"] = {
	formatters: {
		sync_status(value) {
			const color = SYNC_STATUS_COLOR[value] || "grey";
			return `<span class="indicator-pill ${color}">${__(value)}</span>`;
		},
	},
	onload(listview) {
		listview.page.add_inner_button(__("Clean up Deleted"), () => {
			pennylane_cleanup_deleted(listview, "Pennylane Customer Invoice");
		});
	},
};

function pennylane_cleanup_deleted(listview, doctype) {
	frappe.confirm(
		__("This will permanently delete all records marked as Deleted. Continue?"),
		() => {
			frappe.call({
				method: "pennylane.pennylane.api.cleanup_deleted",
				args: { doctype },
				freeze: true,
				freeze_message: __("Cleaning up…"),
				callback(r) {
					if (!r.exc) {
						frappe.show_alert({
							message: __("{0} record(s) deleted", [r.message.deleted]),
							indicator: "green",
						});
						listview.refresh();
					}
				},
			});
		}
	);
}
