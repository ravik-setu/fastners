# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Production Planning',
    'version': '17.1',
    'category': 'MRP',
    'description': 'Production Planning',
    'author': "Setu Consulting Services Pvt. Ltd.",
    'website': 'https://www.setuconsulting.com',
    'depends': ['mrp', 'stock_extended', 'sale_stock', 'stock_account'],
    'data': [
        'security/ir.model.access.csv',
        'views/mrp_production_planning_view.xml',
        'views/mrp_production_view.xml',
        'views/ir_sequence_view.xml',
        'views/mrp_workorder_view.xml',
        'views/res_partner_view.xml',
        'views/production_planing_line_view.xml',
        'views/register_daily_production_view.xml',
        "views/stock_picking_type_view.xml",
        'data/ir_config_parameter.xml',
        'reports/label_template.xml',
        'wizard/additional_product_view.xml',
    ],
    'demo': [
    ],
    'assets': {
        'web.assets_backend': [
            'production_planning/static/src/**/*.js',
        ],
    },
    'web': True,
    # 'installable': True,
    'application': True,
    # 'auto_install': False,
    'license': 'LGPL-3',
}
