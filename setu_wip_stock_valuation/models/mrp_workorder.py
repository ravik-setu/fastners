from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.tests import Form

class Mrpworkorder(models.Model):
    _inherit = 'mrp.workorder'

    name = fields.Char()

    def action_return_component(self):
        if self.production_id.is_src_contain_wip_stock_location():
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'mrp_workorder.additional.product',
                'views': [
                    [self.env.ref('setu_wip_stock_valuation.view_mrp_workorder_return_product_wizard').id, 'form']],
                'name': _('Move To Raw Material'),
                'target': 'new',
                'context': {
                    'default_workorder_id': self.id,
                    'default_type': 'component',
                    'default_company_id': self.company_id.id,
                    'default_is_return': True,
                    'product_ids': self.production_id.move_raw_ids.mapped('product_id').ids,
                    'lot_ids': self.production_id.procurement_group_id.mrp_production_ids.move_raw_ids.move_line_ids.mapped('lot_id')._ids
                }
            }
        raise UserError("Sorry you can not perform Move To Raw Material")

    def record_production(self):
        production_id = self.mapped('production_id')
        is_bom_with_zero_qty = production_id.check_is_bom_with_zero_quantity()
        if is_bom_with_zero_qty:
            production_id.move_raw_ids.write({'quantity_done': self.qty_producing})
            production_reserved_qty = sum(production_id.move_raw_ids.mapped('quantity'))
        res = super(Mrpworkorder, self).record_production()
        if is_bom_with_zero_qty:
            back_order = self.find_latest_backorder(production_id)
            diff_qty = production_reserved_qty - sum(production_id.move_raw_ids.mapped('quantity_done'))
            if back_order and diff_qty:
                self.env["stock.picking"].do_unreserve_and_reserve_based_on_lot(back_order.move_raw_ids,
                                                                                production_id.move_raw_ids.mapped(
                                                                                    'lot_ids'), qty=diff_qty)
        return res

    def find_latest_backorder(self, production_id):
        return production_id.procurement_group_id.mrp_production_ids.filtered(
            lambda mo: mo.backorder_sequence > production_id.backorder_sequence)