frappe.ui.form.on("Pennylane Invoice Line", {
	product(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.product) return;

		frappe.db.get_doc("Pennylane Product", row.product).then((product) => {
			frappe.model.set_value(cdt, cdn, "label", product.label);
			frappe.model.set_value(cdt, cdn, "unit", product.unit || "");
			frappe.model.set_value(cdt, cdn, "vat_rate", product.vat_rate || "");
			if (product.unit_price) {
				frappe.model.set_value(cdt, cdn, "unit_price", product.unit_price);
			}
		});
	},

	quantity(frm, cdt, cdn) { compute_amount(cdt, cdn); },
	unit_price(frm, cdt, cdn) { compute_amount(cdt, cdn); },
	discount(frm, cdt, cdn) { compute_amount(cdt, cdn); },
	discount_type(frm, cdt, cdn) { compute_amount(cdt, cdn); },
});

function compute_amount(cdt, cdn) {
	const row = locals[cdt][cdn];
	const qty = parseFloat(row.quantity) || 0;
	const price = parseFloat(row.unit_price) || 0;
	const discount = parseFloat(row.discount) || 0;
	let amount;

	if ((row.discount_type || "relative") === "absolute") {
		amount = Math.round((qty * price - discount) * 100) / 100;
	} else {
		amount = Math.round(qty * price * (1 - discount / 100) * 100) / 100;
	}

	frappe.model.set_value(cdt, cdn, "currency_amount", amount);
}
