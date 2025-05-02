from odoo import fields, models, api


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    outer_quant_package_id = fields.Many2one('stock.quant.package')
