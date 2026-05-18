# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ReportSaleDetails(models.AbstractModel):
    _inherit = 'report.point_of_sale.report_saledetails'

    def _cs_format_datetime_for_closing_ticket(self, value):
        if not value:
            return ''
        local_dt = fields.Datetime.context_timestamp(self, value)
        return local_dt.strftime('%d/%m/%y %H:%M')

    def _cs_get_closing_ticket_orders(self, session):
        return self.env['pos.order'].search([
            ('session_id', '=', session.id),
            ('state', 'in', ['paid', 'done', 'invoiced']),
        ])

    def _cs_get_payment_summary(self, session, orders):
        payments = self.env['pos.payment'].search([
            ('session_id', '=', session.id),
            ('pos_order_id', 'in', orders.ids),
        ])
        method_summary = {}
        for payment in payments:
            method = payment.payment_method_id
            data = method_summary.setdefault(method.id, {
                'id': method.id,
                'name': method.name,
                'is_cash': bool(method.is_cash_count),
                'amount': 0.0,
                'count': 0,
                'tip': 0.0,
            })
            data['amount'] += payment.amount
            data['count'] += 1

        total_cash = sum(item['amount'] for item in method_summary.values() if item['is_cash'])
        total_card = sum(item['amount'] for item in method_summary.values() if not item['is_cash'])
        cash_count = sum(item['count'] for item in method_summary.values() if item['is_cash'])
        card_count = sum(item['count'] for item in method_summary.values() if not item['is_cash'])

        return {
            'lines': list(method_summary.values()),
            'cash_total': total_cash,
            'card_total': total_card,
            'cash_count': cash_count,
            'card_count': card_count,
            'total': sum(item['amount'] for item in method_summary.values()),
        }

    def _cs_get_company_data(self, company):
        return {
            'name': company.name or '',
            'street': company.street or '',
            'street2': company.street2 or '',
            'city_zip': ' '.join(part for part in [company.zip, company.city] if part),
            'vat': company.vat or '',
        }

    def _cs_get_tax_summary(self, sale_details):
        lines = []
        total_base = 0.0
        total_tax = 0.0
        for tax in sale_details.get('taxes', []):
            base = tax.get('base_amount', 0.0)
            amount = tax.get('tax_amount', 0.0)
            lines.append({
                'name': tax.get('name') or '',
                'base': base,
                'tax': amount,
                'total': base + amount,
            })
            total_base += base
            total_tax += amount
        return {
            'lines': lines,
            'total_base': total_base,
            'total_tax': total_tax,
            'total': total_base + total_tax,
        }

    def _cs_get_cash_move_concept(self, move, session):
        """Concepto del movimiento (motivo Cash In/Out), como en el TPV."""
        ref = (move.payment_ref or '').strip()
        if ref:
            session_name = session.name
            for move_type in ('in', 'out'):
                marker = f'{session_name}-{move_type}-'
                if ref.startswith(marker):
                    concept = ref[len(marker):].strip()
                    if concept:
                        return concept
            prefix = f'{session_name}-'
            if ref.startswith(prefix):
                rest = ref[len(prefix):].lstrip()
                if rest.startswith(('in-', 'out-')):
                    return rest[3:].strip() or ref
                return rest or ref
            return ref
        return (move.name or '').strip()

    def _cs_format_cash_move_line(self, move, session):
        concept = self._cs_get_cash_move_concept(move, session)
        cashier_name = move.partner_id.name or ''
        if not concept and cashier_name:
            concept = cashier_name
        return {
            'concept': concept,
            'cashier_name': cashier_name,
            'name': concept or move.payment_ref or move.name or '',
            'amount': move.amount,
        }

    def _cs_get_cash_move_summary(self, session):
        moves = self.env['account.bank.statement.line'].search([
            ('pos_session_id', '=', session.id),
        ], order='date asc, id asc')
        reason = session.CS_CLOSING_WITHDRAWAL_REASON if hasattr(session, 'CS_CLOSING_WITHDRAWAL_REASON') else 'Retirada cierre de caja'
        inputs = []
        outputs = []
        closing_withdrawals = []
        for move in moves:
            line = self._cs_format_cash_move_line(move, session)
            payment_ref = move.payment_ref or ''
            if move.amount > 0:
                inputs.append(line)
            elif reason and reason.lower() in payment_ref.lower():
                closing_withdrawals.append(line)
            elif move.amount < 0:
                outputs.append(line)

        input_total = sum(line['amount'] for line in inputs)
        output_total = sum(line['amount'] for line in outputs)
        withdrawn = abs(sum(line['amount'] for line in closing_withdrawals))

        return {
            'inputs': inputs,
            'outputs': outputs,
            'closing_withdrawals': closing_withdrawals,
            'input_total': input_total,
            'output_total': output_total,
            'withdrawn': withdrawn,
        }

    def _cs_get_additional_info(self, session, orders, sale_details):
        total_sales = sum(orders.mapped('amount_total'))
        guest_count = 0
        if 'customer_count' in self.env['pos.order']._fields:
            guest_count = sum(orders.mapped('customer_count'))

        order_count = len(orders)
        invoice_count = 0
        if 'account_move' in self.env['pos.order']._fields:
            invoice_count = len(orders.filtered(lambda order: bool(order.account_move)))
        tip_amount = sum(orders.mapped('tip_amount')) if 'tip_amount' in self.env['pos.order']._fields else 0.0
        discount_amount = sale_details.get('discount_amount', 0.0)

        return {
            'guest_count': guest_count,
            'order_count': order_count,
            'invoice_count': invoice_count,
            'average_ticket': total_sales / order_count if order_count else 0.0,
            'average_guest': total_sales / guest_count if guest_count else 0.0,
            'tip_amount': tip_amount,
            'discount_amount': discount_amount,
        }

    def _cs_get_pos_cash_closing_data(self, session, sale_details):
        orders = self._cs_get_closing_ticket_orders(session)
        payment_summary = self._cs_get_payment_summary(session, orders)
        tax_summary = self._cs_get_tax_summary(sale_details)
        cash_moves = self._cs_get_cash_move_summary(session)
        additional = self._cs_get_additional_info(session, orders, sale_details)
        fixed_cash = session.config_id._cs_get_fixed_cash_amount()
        fixed_enabled = session.config_id._cs_fixed_cash_control_is_enabled()

        cash_expected_before_withdrawal = (
            session.cash_register_balance_start
            + payment_summary['cash_total']
            + cash_moves['input_total']
            + cash_moves['output_total']
        )
        cash_counted_with_withdrawal = session.cash_register_balance_end_real + cash_moves['withdrawn']
        cash_difference = cash_counted_with_withdrawal - cash_expected_before_withdrawal

        return {
            'config_name': session.config_id.name,
            'session_name': session.name,
            'session_id': session.id,
            'company': self._cs_get_company_data(session.company_id),
            'opening': {
                'date': self._cs_format_datetime_for_closing_ticket(session.start_at),
                'user': session.user_id.name or '',
            },
            'closing': {
                'date': self._cs_format_datetime_for_closing_ticket(session.stop_at or fields.Datetime.now()),
                'user': session.write_uid.name or self.env.user.name,
            },
            'payments': payment_summary,
            'taxes': tax_summary,
            'additional': additional,
            'cash': {
                'currency_name': session.currency_id.name,
                'transaction_count': payment_summary['cash_count'],
                'opening_cash': session.cash_register_balance_start,
                'cash_sales': payment_summary['cash_total'],
                'cash_in': cash_moves['input_total'],
                'cash_out_extraordinary': cash_moves['output_total'],
                'expected_before_withdrawal': cash_expected_before_withdrawal,
                'counted': cash_counted_with_withdrawal,
                'difference': cash_difference,
                'withdrawn': cash_moves['withdrawn'],
                'next_cash_float': fixed_cash if fixed_enabled else session.cash_register_balance_end_real,
                'inputs': cash_moves['inputs'],
                'outputs': cash_moves['outputs'],
                'closing_withdrawals': cash_moves['closing_withdrawals'],
                'outputs_subtotal': cash_moves['output_total'] - cash_moves['withdrawn'],
            },
            'card': {
                'currency_name': session.currency_id.name,
                'transaction_count': payment_summary['card_count'],
                'sales': payment_summary['card_total'],
                'tip': additional['tip_amount'],
                'total': payment_summary['card_total'],
            },
        }

    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, config_ids=False, session_ids=False, **kwargs):
        sale_details = super().get_sale_details(date_start, date_stop, config_ids, session_ids, **kwargs)
        sessions = self.env['pos.session'].browse(session_ids or []).exists()
        if len(sessions) == 1:
            sale_details['cs_pos_cash_closing'] = self._cs_get_pos_cash_closing_data(sessions, sale_details)
        return sale_details
