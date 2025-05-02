from odoo import models, fields, api, _


class ProductPackaging(models.Model):
    _inherit = "product.packaging"

    box_product_id = fields.Many2one('product.product')