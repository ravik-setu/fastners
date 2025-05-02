from odoo import fields, models, api
from odoo.tools.misc import clean_context, OrderedSet, groupby
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    production_order_id = fields.Many2one('mrp.production', string="Manufacturing Order")
    production_qty = fields.Float(string="Production Qty")
