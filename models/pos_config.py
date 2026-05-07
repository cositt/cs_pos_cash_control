# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class PosConfig(models.Model):
    _inherit = 'pos.config'

    cs_fixed_cash_control_enabled = fields.Boolean(
        string='Activar control de fondo fijo',
        help='Activa el control de apertura y cierre con un fondo fijo para este Punto de Venta.',
    )
    cs_fixed_cash_amount = fields.Monetary(
        string='Fondo fijo de caja',
        currency_field='currency_id',
        help='Importe que debe quedar como fondo fijo de caja al abrir y cerrar el TPV.',
    )
    cs_fixed_opening_cash_enabled = fields.Boolean(
        string='Fondo fijo de apertura',
        help='Obliga a abrir la caja con el importe configurado en este Punto de Venta.',
    )
    cs_fixed_opening_cash_amount = fields.Monetary(
        string='Importe de apertura obligatorio',
        currency_field='currency_id',
        help='Importe de efectivo inicial permitido al abrir la sesion del TPV.',
    )

    def _cs_fixed_cash_control_is_enabled(self):
        self.ensure_one()
        return self.cs_fixed_cash_control_enabled or self.cs_fixed_opening_cash_enabled

    def _cs_get_fixed_cash_amount(self):
        self.ensure_one()
        if self.cs_fixed_cash_control_enabled:
            return self.cs_fixed_cash_amount
        return self.cs_fixed_opening_cash_amount

    @api.constrains(
        'cs_fixed_cash_control_enabled',
        'cs_fixed_cash_amount',
        'cs_fixed_opening_cash_enabled',
        'cs_fixed_opening_cash_amount',
    )
    def _check_cs_fixed_opening_cash_amount(self):
        for config in self:
            if (
                config._cs_fixed_cash_control_is_enabled()
                and float_compare(
                    config._cs_get_fixed_cash_amount(),
                    0.0,
                    precision_rounding=config.currency_id.rounding,
                ) < 0
            ):
                raise ValidationError(_('El fondo fijo de caja no puede ser negativo.'))
