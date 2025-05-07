# -*- coding: utf-8 -*-
{
    'name': "Setu Quality Control Base",

    'summary': """
        Quality Base""",

    'description': """  
        Quality Base
    """,
    'author': 'Setu Consulting Services Pvt. Ltd.',
    'maintainer': 'Setu Consulting Services Pvt. Ltd.',
    'website': 'https://www.setuconsulting.com/',
    'support': 'support@setuconsulting.com',
    'App origin':"Base",
    
    'category': 'Quality',
    'version': '17.0.1.0',
   'license': 'LGPL-3',

    
    'depends': ['stock','setu_quality_control', "mrp", "hr"],

    
    'data': [
        'security/ir.model.access.csv',
        'security/quality_access.xml',
        'views/inspection_plan_view.xml',
        'views/inspection_sheet_revision_view.xml',
        'views/inspection_sheet_view.xml',
        'views/quality_alert_view.xml',
        'views/quality_characteristics_view.xml',
        'views/stock_picking_view.xml'

    ],
}
