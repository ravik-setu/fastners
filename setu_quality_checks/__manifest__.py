# -*- coding: utf-8 -*-
{
    # App information
    'name': 'Quality Checks',
    'version': '17.1',
    'category': '',
    'license': 'OPL-1',
    'description': """This module helps to manage quality checks""",
    'summary': 'This module helps to manage quality checks',

    # Author
    'author': 'Setu Consulting Services Pvt. Ltd.',
    'maintainer': 'Setu Consulting Services Pvt. Ltd.',
    'website': 'https://www.setuconsulting.com/',
    'support': 'support@setuconsulting.com',

    # Dependencies
    'depends': ['mail', 'stock'],

    # Views
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'views/setu_qc_parameter_view.xml',
        'views/setu_quality_check_view.xml',
    ],

    # Technical
    'installable': True,
    'auto_install': False,
    'application': True,
}
