/** @odoo-module **/

import { CashMovePopup } from "@point_of_sale/app/components/popups/cash_move_popup/cash_move_popup";
import { ClosePosPopup } from "@point_of_sale/app/components/popups/closing_popup/closing_popup";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

ClosePosPopup.props = [...ClosePosPopup.props, "cs_cash_control?"];

patch(CashMovePopup.prototype, {
    setup() {
        super.setup();
        const defaults = this.pos.csCashControlCashMoveDefaults;
        if (defaults) {
            this.csCashControlSuggestedDefaults = defaults;
            this.state.type = defaults.type || "out";
            this.state.amount = this.env.utils.formatCurrency(defaults.amount || 0, false);
            this.state.reason = defaults.reason || "";
            this.pos.csCashControlCashMoveDefaults = null;
        }
    },

    onClickButton(type) {
        super.onClickButton(type);
        if (!this.csCashControlSuggestedDefaults) {
            return;
        }
        if (type === "in") {
            this.state.amount = "";
            this.state.reason = "";
            return;
        }
        this.state.amount = this.env.utils.formatCurrency(
            this.csCashControlSuggestedDefaults.amount || 0,
            false
        );
        this.state.reason = this.csCashControlSuggestedDefaults.reason || "";
    },
});

patch(ClosePosPopup.prototype, {
    get csCashControlEnabled() {
        return Boolean(this.props.cs_cash_control?.enabled);
    },

    get csCashControl() {
        return this.props.cs_cash_control || {};
    },

    get csCashControlInputs() {
        return (this.props.default_cash_details.moves || []).filter((move) => move.amount > 0);
    },

    get csCashControlOutputs() {
        return (this.props.default_cash_details.moves || []).filter((move) => move.amount < 0);
    },

    get csSuggestedWithdrawal() {
        return this.csCashControl.suggested_withdrawal || 0;
    },

    get csHasSuggestedWithdrawal() {
        return !this.pos.currency.isZero(this.csSuggestedWithdrawal);
    },

    get csCashClosingDifference() {
        if (!this.props.default_cash_details) {
            return 0;
        }
        return this.getDifference(this.props.default_cash_details.id);
    },

    async confirm() {
        const cashDifference = this.csCashClosingDifference;
        if (
            this.csCashControlEnabled &&
            this.pos.config.cash_control &&
            Number.isFinite(cashDifference) &&
            !this.pos.currency.isZero(cashDifference)
        ) {
            this.dialog.add(AlertDialog, {
                title: _t("Caja descuadrada"),
                body: _t(
                    "No se puede cerrar la caja porque hay una diferencia de %s. La caja debe cuadrar antes de cerrar.",
                    this.env.utils.formatCurrency(Math.abs(cashDifference))
                ),
            });
            return;
        }
        return super.confirm();
    },

    async cashMove() {
        if (this.csCashControlEnabled && this.csHasSuggestedWithdrawal) {
            this.pos.csCashControlCashMoveDefaults = {
                type: "out",
                amount: this.csSuggestedWithdrawal,
                reason: this.csCashControl.closing_withdrawal_reason || _t("Retirada cierre de caja"),
            };
        }
        return super.cashMove();
    },

    async csRegisterSuggestedWithdrawal() {
        if (!this.csCashControlEnabled || !this.csHasSuggestedWithdrawal) {
            this.dialog.add(AlertDialog, {
                title: _t("Retirada sugerida"),
                body: _t("No hay retirada sugerida pendiente."),
            });
            return;
        }
        const employeeId = this.pos.config.module_pos_hr ? this.pos.getCashier().id : false;
        await this.pos.data.call(
            "pos.session",
            "cs_register_suggested_cash_out",
            [this.pos.session.id, employeeId],
            {},
            true
        );
        this.dialog.closeAll();
        this.pos.closeSession();
    },
});
