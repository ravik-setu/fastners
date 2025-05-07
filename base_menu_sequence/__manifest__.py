{
    'name': 'Base Menu Sequence',
    'version': '17.1',
    'license': 'LGPL-3',
    'summary': 'Rearranges main menu sequence and renames Discuss to Messages',
    'author': "Setu Consulting Services Pvt. Ltd.",
    'website': 'https://www.setuconsulting.com',
    'category': 'Base',
    'depends': ['base', 'purchase', 'stock', 'mrp', 'sale_management', 'account', 'mail', 'setu_product_packages', 'production_planning'],
    'data': [
        'data/menu_sequence.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}


