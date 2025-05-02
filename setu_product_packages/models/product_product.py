from odoo import fields, models, api

class ProductProduct(models.Model):
    _inherit = 'product.product'

    weight = fields.Float('Weight', digits='Stock Weight', tracking=True)
    put_in_pack = fields.Boolean(string="Put In Pack", related='product_tmpl_id.put_in_pack', readonly=False, store=True)
    put_in_pack_product_id = fields.Many2one("product.product", string="Put in Pack Product",
                                             related='product_tmpl_id.put_in_pack_product_id', readonly=False, store=True)