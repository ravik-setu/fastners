from odoo import models, fields, api


class SetuPackageLine(models.Model):
    _name = 'setu.package.line'
    description = 'Setu Package Line'

    product_id = fields.Many2one('product.product')
    tracking = fields.Selection(related='product_id.tracking')
    package_id = fields.Many2one('setu.product.package')
    location_id = fields.Many2one("stock.location", related="package_id.source_location_id")
    lot_ids = fields.Many2many('stock.lot')
    product_package_id = fields.Many2one('product.packaging')
    package_qty = fields.Float()
    company_id = fields.Many2one(comodel_name="res.company", default=lambda self: self.env.company)
    weight = fields.Float(digits=(4, 4))
    quant_package_id = fields.Many2one("stock.quant.package")

