frappe.listview_settings["Pennylane Sync Log"] = {
	onload(listview) {
		listview.page.add_inner_button(__("Cleanup Success Logs"), () => {
			frappe.confirm(
				__("Delete all Success logs? Failed logs will be kept."),
				() => {
					frappe.call({
						method: "pennylane.pennylane.api.cleanup_sync_logs",
						args: { keep_failed: true, older_than_days: 0 },
						callback(r) {
							if (!r.exc) {
								frappe.show_alert({
									message: __("Cleanup queued — the list will refresh shortly."),
									indicator: "blue",
								});
								setTimeout(() => listview.refresh(), 3000);
							}
						},
					});
				}
			);
		});

		listview.page.add_inner_button(__("Cleanup All Logs"), () => {
			frappe.confirm(
				__("Delete ALL logs including Failed ones? This cannot be undone."),
				() => {
					frappe.call({
						method: "pennylane.pennylane.api.cleanup_sync_logs",
						args: { keep_failed: false, older_than_days: 0 },
						callback(r) {
							if (!r.exc) {
								frappe.show_alert({
									message: __("Cleanup queued — the list will refresh shortly."),
									indicator: "blue",
								});
								setTimeout(() => listview.refresh(), 3000);
							}
						},
					});
				}
			);
		});
	},
};
