const SYNC_STATUS_COLOR = {
	Synced: "green",
	Pending: "orange",
	Failed: "red",
	Deleted: "purple",
};

frappe.listview_settings["Pennylane Customer Quote"] = {
	formatters: {
		sync_status(value) {
			const color = SYNC_STATUS_COLOR[value] || "grey";
			return `<span class="indicator-pill ${color}">${__(value)}</span>`;
		},
	},
	onload(listview) {
		listview.page.add_inner_button(__("Sync All"), () => {
			pennylane_sync_all(listview, "Pennylane Customer Quote");
		});

		frappe.call({
			method: "frappe.client.get_count",
			args: { doctype: "Pennylane Customer Quote", filters: { sync_status: "Deleted" } },
			callback(r) {
				if (r.message > 0) {
					const btn = listview.page.add_inner_button(__("Clean up Deleted"), () => {
						pennylane_cleanup_deleted(listview, "Pennylane Customer Quote", btn);
					});
				}
			},
		});
	},
};

function pennylane_sync_all(listview, doctype) {
	frappe.call({
		method: "pennylane.pennylane.api.sync_all",
		args: { doctype },
		freeze: true,
		freeze_message: __("Syncing…"),
		callback(r) {
			if (!r.exc) {
				frappe.show_alert({ message: __("Sync started in background"), indicator: "blue" });
			}
		},
	});
}

function pennylane_cleanup_deleted(listview, doctype, btn) {
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
						btn && btn.remove();
						listview.refresh();
					}
				},
			});
		}
	);
}
