{
    'name': "Setu Product Packages",
    'summary': "",
    'category': 'Inventory',
    "author": "Setu Consulting Services Pvt. Ltd.",
    "version": "17.0",
    'depends': ['stock_extended', 'barcodes', 'mrp'],
    "license": "LGPL-3",
    'data': [
        'data/setu_product_package.xml',
        'security/ir.model.access.csv',
        'security/ir_rule_view.xml',
        'views/setu_product_package.xml',
        'views/product_packaging_view.xml',
        'views/stock_package_type_view.xml',
        'views/stock_quant_package_view.xml',
        'views/stock_picking_type_views.xml',
        'views/product_template_views.xml',
        'views/stock_picking.xml',
        'reports/stock_report_views.xml',
        'wizard/package_weight_wizard_view.xml'
    ],
    'assets': {
        'web.assets_backend': [
            "setu_product_packages/static/src/js/setu_barcode_handler_field.js",
            "setu_product_packages/static/src/js/setu_barcode_handler_field_view.xml",
            "setu_product_packages/static/src/css/barcode.scss"
        ],
    },
    "installable": True,
    "application": True,
}
