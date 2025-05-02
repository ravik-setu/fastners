from odoo import fields, models, api
import logging

from odoo.exceptions import UserError

_logger = logging.getLogger("Register Production")


class RegisterDailyProduction(models.Model):
    _name = 'register.daily.production'
    _description = 'Register Daily Production'

    planning_id = fields.Many2one("mrp.production.planning")
    planning_line = fields.Many2one("mrp.production.planning.line")
    production_id = fields.Many2one("mrp.production")
    workorder_id = fields.Many2one("mrp.workorder")
    qty_produced = fields.Float("Qty Produced")
    return_to_stock = fields.Boolean(string="Move Product To Raw Material?")
    return_quantity = fields.Float(string="Return Quantity")
    product_id = fields.Many2one("product.product", related="planning_line.product_id", string="Product")

    def register_daily_production(self):
        action = {}
        mo = self.production_id
        mo.raise_error_if_multiple_lot_found()
        if mo.product_id.tracking != 'none' and not mo.lot_producing_id:
            mo.action_generate_serial()
        if self.qty_produced > 0:
            mo.qty_producing = self.qty_produced
            mo._onchange_producing()
        scrp_qty = 0
        to_consume = sum(mo.move_raw_ids.mapped('should_consume_qty')) if self.qty_produced else 0
        total_reserved = mo.get_available_component_qty_for_return()
        if self.qty_produced and to_consume > total_reserved:
            raise UserError(
                "You are trying to use more quantity then reserved\nReserved: {},\nConsume: {}".format(total_reserved,
                                                                                                       to_consume))
        _logger.info(
            "========= Start Register Production For MO {}:{} Quantity: {}, Reserved: {}".format(mo.id, mo.name,
                                                                                                 self.qty_produced,
                                                                                                 total_reserved))
        need_reserve_in_backorder = total_reserved - scrp_qty
        if self.return_to_stock:
            scrp_qty = total_reserved - (self.return_quantity + to_consume)
            to_consume = total_reserved - (self.return_quantity + scrp_qty if scrp_qty > 0 else self.return_quantity)
            need_reserve_in_backorder -= (scrp_qty + to_consume)
        _logger.info("MO {}: {}, Scrap Quantity {},Should Consume {}, To Consume {}".format(mo.id, mo.name, scrp_qty,
                                                                                            mo.move_raw_ids.mapped(
                                                                                                'should_consume_qty'),
                                                                                            to_consume))
        if scrp_qty > 0:
            mo.product_move_to_scrap(scrp_qty, mo.move_raw_ids.lot_ids)
        if self.qty_produced > 0:
            pending_data = {}
            for move in mo.move_raw_ids:
                if need_reserve_in_backorder:
                    product_id = move.product_id
                    if product_id.id not in pending_data.keys():
                        pending_data.update({product_id.id: {'lot_ids': [], 'quantity': need_reserve_in_backorder}})
                    if move.lot_ids.ids not in pending_data[product_id.id]['lot_ids']:
                        pending_data[product_id.id]['lot_ids'] += move.lot_ids.ids
                move.move_line_ids.write({'quantity': to_consume})
                mo.move_raw_ids.write({'picked': True})
            action = mo.with_context(avoid_warning=True).mark_done_and_create_backorder_if_needed()
            self.planning_line.running_production_id = self.planning_line.find_latest_backorder() or mo.id
            self.reserve_backorder_based_on_pending_qty(
                pending_data) if self.planning_line.running_production_id and mo.id != self.planning_line.running_production_id.id else self.planning_line.button_stop()
        if self.return_to_stock and self.return_quantity:
            try:
                return self.planning_line.running_production_id.return_product_to_stock(self.return_quantity)
            except Exception as e:
                raise UserError(e)
            return action
        return mo

    def reserve_backorder_based_on_pending_qty(self, pending_data):
        production_id = self.planning_line.find_latest_backorder()
        product_ids = production_id.move_raw_ids.mapped('product_id')
        for product in product_ids:
            prod_moves = production_id.move_raw_ids.filtered(lambda move: move.product_id.id == product.id)
            if product.id in pending_data.keys():
                lot_ids = self.env['stock.lot'].search([('id', 'in', pending_data[product.id]['lot_ids'])])
                self.env["stock.picking"].do_unreserve_and_reserve_based_on_lot(prod_moves, lot_ids,
                                                                                qty=pending_data[product.id][
                                                                                    'quantity'])
