# -*- coding: utf-8 -*-
{
    'name': 'Cierre de Caja TPV',
    'version': '19.0.1.0.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Control de caja para apertura, cierre e impresion del TPV',
    'description': """
Control de caja por Punto de Venta.

Permite configurar fondo fijo por TPV, controlar apertura y cierre, calcular
retirada sugerida y personalizar el ticket impreso de cierre de caja.
    """,
    'author': 'Cositt Technology',
    'website': 'https://cositt.com',
    'license': 'LGPL-3',
    'depends': [
        'point_of_sale',
    ],
    'data': [
        'views/pos_config_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'cs_pos_cash_control/static/src/js/opening_control_popup.js',
            'cs_pos_cash_control/static/src/js/cash_control_closing.js',
            'cs_pos_cash_control/static/src/js/pos_cash_closing_report.js',
            'cs_pos_cash_control/static/src/xml/opening_control_popup.xml',
            'cs_pos_cash_control/static/src/xml/cash_control_closing.xml',
            'cs_pos_cash_control/static/src/xml/pos_cash_closing_report.xml',
            'cs_pos_cash_control/static/src/scss/cash_control.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
