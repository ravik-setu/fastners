from odoo import fields, models, api


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    sequence_for_inspection_plan = fields.Many2one('ir.sequence')
    sequence_for_inspection_sheet = fields.Many2one('ir.sequence')

    code = fields.Selection(required=False)