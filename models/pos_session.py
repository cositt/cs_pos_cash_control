# -*- coding: utf-8 -*-

from odoo import models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class PosSession(models.Model):
    _inherit = 'pos.session'

    CS_CLOSING_WITHDRAWAL_REASON = 'Retirada cierre de caja'

    def _cs_fixed_opening_cash_message(self, amount):
        self.ensure_one()
        amount_formatted = self.currency_id.format(amount)
        return _(
            'El fondo de apertura debe ser de %(amount)s. No se puede abrir la caja con un importe distinto.',
            amount=amount_formatted,
        )

    def _cs_check_fixed_opening_cash(self, cashbox_value):
        self.ensure_one()
        config = self.config_id
        if not config._cs_fixed_cash_control_is_enabled() or self.rescue:
            return

        fixed_amount = config._cs_get_fixed_cash_amount()
        if float_compare(cashbox_value, fixed_amount, precision_rounding=self.currency_id.rounding) != 0:
            raise UserError(self._cs_fixed_opening_cash_message(fixed_amount))

    def _cs_has_cash_closing_difference(self):
        self.ensure_one()
        return not self.currency_id.is_zero(self.cash_register_difference)

    def _cs_cash_control_blocks_closing(self):
        self.ensure_one()
        return (
            self.config_id.cash_control
            and self.config_id._cs_fixed_cash_control_is_enabled()
            and not self.rescue
            and self._cs_has_cash_closing_difference()
        )

    def _cs_cash_closing_difference_message(self):
        self.ensure_one()
        return _(
            'No se puede cerrar la caja porque hay una diferencia de %(amount)s. '
            'La caja debe cuadrar antes de cerrar.',
            amount=self.currency_id.format(abs(self.cash_register_difference)),
        )

    def _cs_cash_closing_difference_response(self):
        self.ensure_one()
        return {
            'successful': False,
            'title': _('Caja descuadrada'),
            'message': self._cs_cash_closing_difference_message(),
            'redirect': False,
        }

    def _cs_check_cash_control_balanced_closing(self):
        for session in self:
            if session._cs_cash_control_blocks_closing():
                raise UserError(session._cs_cash_closing_difference_message())

    def action_pos_session_open(self):
        res = super().action_pos_session_open()
        for session in self.filtered(
            lambda session: (
                session.state == 'opening_control'
                and not session.rescue
                and session.config_id.cash_control
                and session.config_id._cs_fixed_cash_control_is_enabled()
            )
        ):
            session.cash_register_balance_start = session.config_id._cs_get_fixed_cash_amount()
        return res

    def _set_opening_control_data(self, cashbox_value: int, notes: str):
        for session in self:
            session._cs_check_fixed_opening_cash(cashbox_value)
        return super()._set_opening_control_data(cashbox_value, notes)

    def _cs_get_cash_control_totals(self):
        self.ensure_one()
        cash_moves = self.sudo().statement_line_ids
        cash_in_total = sum(cash_moves.filtered(lambda line: line.amount > 0).mapped('amount'))
        cash_out_total = sum(cash_moves.filtered(lambda line: line.amount < 0).mapped('amount'))
        opening_cash = self.cash_register_balance_start
        cash_payment_method = self.payment_method_ids.filtered('is_cash_count')[:1]
        cash_sales = 0.0
        if cash_payment_method:
            cash_payments = self.env['pos.payment'].search([
                ('session_id', '=', self.id),
                ('payment_method_id', '=', cash_payment_method.id),
                ('pos_order_id.state', 'in', ['paid', 'invoiced', 'done']),
            ])
            cash_sales = sum(cash_payments.mapped('amount'))
        expected_cash = opening_cash + cash_sales + cash_in_total + cash_out_total

        fixed_cash_amount = self.config_id._cs_get_fixed_cash_amount()
        suggested_withdrawal = max(expected_cash - fixed_cash_amount, 0.0)
        if self.currency_id.is_zero(suggested_withdrawal):
            suggested_withdrawal = 0.0

        return {
            'enabled': bool(self.config_id._cs_fixed_cash_control_is_enabled() and self.config_id.cash_control),
            'fixed_cash_amount': fixed_cash_amount,
            'opening_cash': opening_cash,
            'cash_sales': cash_sales,
            'cash_in_total': cash_in_total,
            'cash_out_total': cash_out_total,
            'expected_cash': expected_cash,
            'suggested_withdrawal': suggested_withdrawal,
            'next_cash_float': fixed_cash_amount if suggested_withdrawal or expected_cash >= fixed_cash_amount else expected_cash,
            'closing_withdrawal_reason': self.CS_CLOSING_WITHDRAWAL_REASON,
        }

    def get_closing_control_data(self):
        data = super().get_closing_control_data()
        self.ensure_one()
        if data.get('default_cash_details'):
            data['cs_cash_control'] = self._cs_get_cash_control_totals()
        return data

    def post_closing_cash_details(self, counted_cash):
        result = super().post_closing_cash_details(counted_cash)
        self.ensure_one()
        if result.get('successful') and self._cs_cash_control_blocks_closing():
            return self._cs_cash_closing_difference_response()
        return result

    def update_closing_control_state_session(self, notes):
        self._cs_check_cash_control_balanced_closing()
        return super().update_closing_control_state_session(notes)

    def close_session_from_ui(self, bank_payment_method_diff_pairs=None):
        self._cs_check_cash_control_balanced_closing()
        return super().close_session_from_ui(bank_payment_method_diff_pairs)

    def get_cash_in_out_list(self):
        cash_in_out_list = super().get_cash_in_out_list()
        StatementLine = self.env['account.bank.statement.line']
        if 'employee_id' not in StatementLine._fields:
            return cash_in_out_list

        for cash_in_out in cash_in_out_list:
            cash_move = StatementLine.browse(cash_in_out['id'])
            if cash_move.employee_id:
                cash_in_out['cashier_name'] = cash_move.employee_id.name
        return cash_in_out_list

    def cs_get_cash_control_totals(self):
        self.ensure_one()
        return self._cs_get_cash_control_totals()

    def cs_register_suggested_cash_out(self, employee_id=False):
        self.ensure_one()
        totals = self._cs_get_cash_control_totals()
        amount = totals['suggested_withdrawal']
        if not totals['enabled'] or self.currency_id.is_zero(amount):
            return totals

        partner_id = self.env.user.partner_id.id
        employee = False
        if employee_id and 'hr.employee' in self.env.registry:
            employee = self.env['hr.employee'].browse(employee_id).exists()
        if employee and employee.work_contact_id:
            partner_id = employee.work_contact_id.id

        extras = {
            'formattedAmount': self.currency_id.format(amount),
            'translatedType': 'out',
        }
        if employee:
            extras['employee_id'] = employee.id

        self.try_cash_in_out(
            'out',
            amount,
            self.CS_CLOSING_WITHDRAWAL_REASON,
            partner_id,
            extras,
        )
        return self._cs_get_cash_control_totals()
