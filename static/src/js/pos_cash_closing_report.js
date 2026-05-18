/** @odoo-module **/

import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { SaleDetailsButton } from "@point_of_sale/app/components/navbar/sale_details_button/sale_details_button";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { patch } from "@web/core/utils/patch";
import {
    fetchSessionSaleDetails,
    renderClosingReceiptElement,
} from "./closing_receipt_html_preview";

/**
 * Odoo 19: el menú hamburguesa «Print Report» llama a Navbar.showSaleDetails() → handleSaleDetails(),
 * no a SaleDetailsButton.onClick. Por eso el ticket custom no se activaba nunca si el usuario
 * imprimía solo desde ese menú.
 */
async function printPosSessionClosingReceipt(pos, hardwareProxy, dialog) {
    const saleDetails = await fetchSessionSaleDetails(pos);
    const report = renderClosingReceiptElement(saleDetails, pos);
    const { successful, message } = await hardwareProxy.printer.printReceipt(report);
    if (!successful) {
        dialog.add(AlertDialog, {
            title: message.title,
            body: message.body,
        });
    }
}

patch(Navbar.prototype, {
    async showSaleDetails() {
        await printPosSessionClosingReceipt(this.pos, this.hardwareProxy, this.dialog);
    },
});

patch(SaleDetailsButton.prototype, {
    async onClick() {
        await printPosSessionClosingReceipt(this.pos, this.hardwareProxy, this.dialog);
    },
});
