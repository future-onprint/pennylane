frappe.ui.form.on("Pennylane Settings", {
	refresh(frm) {
		_set_connection_status_color(frm);
		_add_connection_buttons(frm);

		if (frm.doc.enable_webhooks) {
			_add_webhook_buttons(frm);
			_set_webhook_status_indicator(frm);
		}
	},
});

// ------------------------------------------------------------------
// Connection
// ------------------------------------------------------------------

function _add_connection_buttons(frm) {
	frm.add_custom_button(__("Test Connection"), () => {
		frm.call("test_connection").then((r) => {
			const status = r.message;
			frappe.show_alert({
				message: __("Connection status: {0}", [__(status)]),
				indicator: status === "Connected" ? "green" : "red",
			});
			frm.reload_doc();
		});
	}, __("Actions"));

	frm.add_custom_button(__("Run Full Sync"), () => {
		const anySelected =
			frm.doc.force_sync_customers ||
			frm.doc.force_sync_invoices ||
			frm.doc.force_sync_quotes ||
			frm.doc.force_sync_products;

		if (!anySelected) {
			frappe.msgprint({
				title: __("No resource selected"),
				message: __("Select at least one resource to re-import in the Advanced tab, Force Full Re-sync section."),
				indicator: "orange",
			});
			return;
		}

		frappe.confirm(
			__("This will re-import all selected resources from Pennylane and may take several minutes. Continue?"),
			() => {
				frm.call("run_full_sync").then((r) => {
					const jobs = r.message?.queued || [];
					frappe.show_alert({
						message: __("Full sync queued for: {0}", [jobs.join(", ") || __("nothing")]),
						indicator: "blue",
					});
					frm.reload_doc();
				});
			}
		);
	}, __("Actions"));
}

// ------------------------------------------------------------------
// Webhooks
// ------------------------------------------------------------------

function _add_webhook_buttons(frm) {
	frm.add_custom_button(__("Refresh Status"), () => {
		frm.call("refresh_webhook_status").then((r) => {
			const sub = r.message;
			if (sub) {
				frappe.show_alert({
					message: __("Webhook subscription #{0} is active.", [sub.id]),
					indicator: "green",
				});
			} else {
				frappe.show_alert({
					message: __("No active webhook subscription found in Pennylane."),
					indicator: "orange",
				});
			}
			frm.reload_doc();
		});
	}, __("Webhooks"));

	frm.add_custom_button(__("Re-register"), () => {
		frappe.confirm(
			__("This will delete the existing webhook subscription and create a new one. The signing secret will change. Continue?"),
			() => {
				frm.call("reregister_webhook").then((r) => {
					const res = r.message;
					frappe.show_alert({
						message: __("Webhook re-registered (#{0}).", [res?.id]),
						indicator: "green",
					});
					frm.reload_doc();
				});
			}
		);
	}, __("Webhooks"));
}

function _set_webhook_status_indicator(frm) {
	const id = frm.doc.webhook_subscription_id;
	const field = frm.get_field("webhook_subscription_id");
	if (!field) return;

	const color = id ? "var(--green-500)" : "var(--orange-500)";
	const label = id
		? `<span style="color:${color}">&#10003; ${__("Registered")} (#${id})</span>`
		: `<span style="color:${color}">&#9679; ${__("Not registered")}</span>`;

	field.set_description(label);
}

// ------------------------------------------------------------------
// Connection status colour
// ------------------------------------------------------------------

function _set_connection_status_color(frm) {
	const status = frm.doc.connection_status;
	if (!status) return;

	const color_map = {
		"Connected": "green",
		"Failed": "red",
		"Not Tested": "orange",
	};
	const color = color_map[status] || "grey";

	frm.get_field("connection_status")?.$input_wrapper
		?.find(".control-value")
		?.css("color", `var(--${color}-500)`);
}
