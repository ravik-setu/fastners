from odoo import fields, models, api


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    auto_package = fields.Boolean(string="Auto Package")
    show_create_package = fields.Boolean(string='Show Create Package')
