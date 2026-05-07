/** @odoo-module **/

import { SaleDetailsButton } from "@point_of_sale/app/components/navbar/sale_details_button/sale_details_button";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { renderToElement } from "@web/core/utils/render";
import { patch } from "@web/core/utils/patch";

patch(SaleDetailsButton.prototype, {
    async onClick() {
        const saleDetails = await this.pos.data.call(
            "report.point_of_sale.report_saledetails",
            "get_sale_details",
            [false, false, false, [this.pos.session.id]]
        );
        const template = saleDetails.cs_pos_cash_closing
            ? "cs_pos_cash_control.PosCashClosingReport"
            : "point_of_sale.SaleDetailsReport";
        const report = renderToElement(
            template,
            Object.assign({}, saleDetails, {
                date: new Date().toLocaleString(),
                pos: this.pos,
                formatCurrency: this.pos.env.utils.formatCurrency,
            })
        );
        const { successful, message } = await this.hardwareProxy.printer.printReceipt(report);
        if (!successful) {
            this.dialog.add(AlertDialog, {
                title: message.title,
                body: message.body,
            });
        }
    },
});
