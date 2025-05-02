from odoo import fields, models, api
from odoo.tools.misc import OrderedSet
from odoo.tools.float_utils import float_is_zero


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def do_unreserve_and_reserve_based_on_lot(self, move_ids=[], lot_ids=False, avoid_unreserve=False, qty= 0):
        move_ids = move_ids or self.move_ids
        assigned_moves_ids = OrderedSet()
        partially_available_moves_ids = OrderedSet()
        if not lot_ids:
            purchase = self.find_purchase_based_on_origin()
            lot_ids = purchase.source_picking_id.mapped('move_line_nosuggest_ids').mapped('lot_id')
        if not avoid_unreserve:
            move_ids._do_unreserve()
        for move in move_ids or self.move_ids:
            need = qty or move.product_qty - sum(move.move_line_ids.mapped('quantity'))
            for lot_id in lot_ids:
                if not need:
                    continue
                exclude = dict(move._context)
                exclude.update({'exclude_package': True})
                available_quantity = move.with_context(exclude)._get_available_quantity(move.location_id,
                                                                                        lot_id=lot_id,
                                                                                        strict=True)
                if float_is_zero(available_quantity, precision_rounding=move.product_uom.rounding):
                    continue
                taken_quantity = move.with_context(exclude)._update_reserved_quantity(min(need, available_quantity),
                                               location_id=move.location_id,
                                               lot_id=lot_id, strict=False)
                if float_is_zero(taken_quantity, precision_rounding=move.product_uom.rounding):
                    continue
                if float_is_zero(need - taken_quantity, precision_rounding=move.product_uom.rounding):
                    assigned_moves_ids.add(move.id)
                    break
                need -= taken_quantity
                partially_available_moves_ids.add(move.id)
        StockMove = self.env["stock.move"]
        StockMove.browse(partially_available_moves_ids).write({'state': 'partially_available'})
        StockMove.browse(assigned_moves_ids).write({'state': 'assigned'})
