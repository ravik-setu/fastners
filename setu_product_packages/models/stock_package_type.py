from odoo import fields, models


class PackageType(models.Model):
    _inherit = 'stock.package.type'

    package_product_id = fields.Many2one('product.product')
    prefix = fields.Char(string='Prefix', tracking=True)
    is_visible_package_qty = fields.Boolean(string='Is Package Qty Visible', help="Set package qty in package PDF.", default=True)
    is_visible_package_weight = fields.Boolean(string='Is Package Weight Visible',
                                               help="Set package qty in package PDF.", default=True)
    is_outer_box = fields.Boolean(string="Outer Box")
