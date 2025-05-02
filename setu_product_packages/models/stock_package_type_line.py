from odoo import fields, models, api


class StockPackageTypeLine(models.Model):
    _name = 'stock.package.type.line'
    _description = 'Product configurations for a package type'

    product_id = fields.Many2one('product.product')
    package_type_id = fields.Many2one('stock.package.type')
    packaging_id = fields.Many2one('product.packaging', string="Package")
    box_quantity = fields.Float(string='Box Quantity')
