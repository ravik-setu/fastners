# -*- coding: utf-8 -*-
{
    # App information
    'name': 'Gate Entry Management',
    'version': '17.1',
    'category': 'Purchase',
    'license': 'OPL-1',
    'description': """This module helps to manage gate entries""",
    'summary': 'This module helps to manage to gate entries',

    # Author
    'author': 'Setu Consulting Services Pvt. Ltd.',
    'maintainer': 'Setu Consulting Services Pvt. Ltd.',
    'website': 'https://www.setuconsulting.com/',
    'support': 'support@setuconsulting.com',

    # Dependencies
    'depends': ['base', 'mail'],

    # Views
    'data': [
        'data/sequence.xml',
        'security/ir.model.access.csv',
        'security/res_groups.xml',

        'views/main_menu_views.xml',
        'views/setu_gate_entry_register_views.xml',

        'report/visitor_gate_pass_report.xml',
        'report/inward_gate_pass_report.xml',
        'report/gate_pass_report.xml',
    ],
    # WEB MENU
    'assets': {
        'web.assets_backend': [
            'setu_gate_entry_management/static/src/js/gate_entry_dashboard.js',
            'setu_gate_entry_management/static/src/xml/gate_entry_content.xml',
        ],
    },
    # Technical
    'installable': True,
    'auto_install': False,
    'application': True,
}
