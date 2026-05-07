/** @odoo-module **/

import { OpeningControlPopup } from "@point_of_sale/app/components/popups/opening_control_popup/opening_control_popup";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { parseFloat } from "@web/views/fields/parsers";

patch(OpeningControlPopup.prototype, {
    setup() {
        super.setup();
        this._csApplyFixedOpeningCash();
    },

    get csFixedOpeningCashEnabled() {
        return Boolean(
            (this.pos.config.cs_fixed_cash_control_enabled || this.pos.config.cs_fixed_opening_cash_enabled)
            && this.cashMethodCount
        );
    },

    get csFixedOpeningCashAmount() {
        if (this.pos.config.cs_fixed_cash_control_enabled) {
            return this.pos.config.cs_fixed_cash_amount || 0;
        }
        return this.pos.config.cs_fixed_opening_cash_amount || 0;
    },

    _csApplyFixedOpeningCash() {
        if (this.csFixedOpeningCashEnabled) {
            this.state.openingCash = this.env.utils.formatCurrency(
                this.csFixedOpeningCashAmount,
                false
            );
        }
    },

    _csFixedOpeningCashMessage() {
        const amount = this.env.utils.formatCurrency(this.csFixedOpeningCashAmount);
        return _t(
            "El fondo de apertura debe ser de %s. No se puede abrir la caja con un importe distinto.",
            amount
        );
    },

    _csOpeningCashMatchesFixedAmount() {
        const openingCash = parseFloat(this.state.openingCash);
        return Math.abs(openingCash - this.csFixedOpeningCashAmount) < 0.000001;
    },

    async confirm() {
        if (this.csFixedOpeningCashEnabled && !this._csOpeningCashMatchesFixedAmount()) {
            this.dialog.add(AlertDialog, {
                title: _t("Fondo fijo de apertura"),
                body: this._csFixedOpeningCashMessage(),
            });
            this._csApplyFixedOpeningCash();
            return;
        }
        return super.confirm();
    },

    openDetailsPopup() {
        if (this.csFixedOpeningCashEnabled) {
            this.dialog.add(AlertDialog, {
                title: _t("Fondo fijo de apertura"),
                body: this._csFixedOpeningCashMessage(),
            });
            this._csApplyFixedOpeningCash();
            return;
        }
        return super.openDetailsPopup();
    },

    handleInputChange() {
        if (this.csFixedOpeningCashEnabled) {
            this._csApplyFixedOpeningCash();
            return;
        }
        return super.handleInputChange();
    },
});
