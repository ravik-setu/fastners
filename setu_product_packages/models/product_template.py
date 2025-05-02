from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    auto_package = fields.Boolean(string="Auto Package")
    put_in_pack = fields.Boolean(string="Put In Pack")
    put_in_pack_product_id = fields.Many2one("product.product", string="Put in Pack Product")
