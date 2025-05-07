from odoo import fields, models, api


class StockLocation(models.Model):
    _inherit = 'stock.location'

    avoid_negative_quantity = fields.Boolean(default=False,copy=False)

