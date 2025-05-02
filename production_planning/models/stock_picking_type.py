from odoo import fields, models, api


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    use_parent_mo_lot = fields.Boolean(string="Use Actual MO Lot")
