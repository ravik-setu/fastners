from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_done(self, cancel_backorder=False):
        not_available_products = ''
        for move_line in self.move_line_ids.filtered(
                lambda m_line: m_line.location_id.usage == 'internal' and m_line.location_id.avoid_negative_quantity and m_line.product_id.detailed_type == 'product'):
            domain = [('product_id', '=', move_line.product_id.id),
                      ('product_id.detailed_type', '=', 'product'), ('quantity', '>', 0),
                      ('location_id.usage', '=', 'internal'), ('location_id', '=', move_line.location_id.id)]
            if move_line.lot_id:
                domain.append(('lot_id', '=', move_line.lot_id.id))
            quants = self.env['stock.quant'].search(domain)
            available_qty = sum(quants.mapped('quantity'))
            if available_qty < round(move_line.quantity, 6):
                not_available_products += '\n {} available {}'.format(move_line.product_id.name, available_qty)
        if not_available_products:
            raise ValidationError(
                _(f'Following Products has/have not enough stock in the system, please contact your Inventory Manager.\n{not_available_products}'))
        return super()._action_done(cancel_backorder=cancel_backorder)
