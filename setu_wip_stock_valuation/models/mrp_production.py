from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.tests import Form
import logging
_logger = logging.getLogger(__name__)


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    is_bom_component_available = fields.Boolean(compute="_compute_is_bom_component_available")

    @api.depends("move_raw_ids.quantity")
    def _compute_is_bom_component_available(self):
        for rec in self:
            rec.is_bom_component_available = True if rec.get_available_component_qty_for_return() else False

    def create_internal_transfer(self, product_id, qty, lot_id, is_return=False):
        """
        Author: Gaurav Vipani | Date: 14th Aug, 2023
        Purpose: create internal transfer if component raw material type
        """
        is_raw_material_product = self.bom_id.bom_line_ids.mapped("product_id").filtered(
            lambda prod: prod.is_raw_material)
        location_id = product_id.destination_location_id if not is_return else self.location_src_id
        dest_location_id = self.location_src_id if not is_return else product_id.destination_location_id
        if location_id.id == dest_location_id.id or not is_raw_material_product:
            return False
        try:
            self.create_internal_picking_and_validate(product_id, location_id, dest_location_id,
                                                      self.procurement_group_id, qty, lot_id, is_raw_material_product)
        except Exception as e:
            raise UserError(e)

    def _prepare_internal_picking_vals(self, picking_type, location_id, location_dest_id, origin_name=False,
                                       group_id=False):
        """
        Author : Gaurav Vipani | Date : 14th Aug,2023
        Purpose: prepare internal picking vals
        """
        return {
            'picking_type_id': picking_type.id,
            'user_id': False,
            'date': fields.datetime.today(),
            'origin': self.name or origin_name,
            'location_dest_id': location_dest_id.id,
            'location_id': location_id.id,
            'company_id': self.company_id.id,
            'group_id': group_id.id or False,
            'production_order_id': self.id,
            'production_qty': self.product_qty
        }

    def _prepare_stock_move_vals(self, product_id, qty, location_id, location_dest_id, picking_id, group_id):
        """
        Author : Gaurav Vipani | Date : 14th Aug,2023
        Purpose: prepare stock move vals
        """
        return {
            'name': product_id.display_name,
            'product_id': product_id.id,
            'product_uom_qty': qty,
            'product_uom': product_id.uom_id.id,
            'location_id': location_id.id,
            'location_dest_id': location_dest_id.id,
            'picking_id': picking_id.id,
            'state': picking_id.state,
            'picking_type_id': picking_id.picking_type_id.id,
            'company_id': picking_id.company_id.id,
            'partner_id': picking_id.partner_id.id or False,
            'group_id': group_id.id or False
        }

    def create_internal_picking_and_validate(self, product_id, location_id, dest_location_id, group_id, qty, lot_id,
                                             is_raw_material_product=False):
        stock_picking_env = self.env["stock.picking"]
        picking_type = self.env["stock.picking.type"].search(
            [('code', '=', 'internal'), ('company_id', '=', self.company_id.id)], limit=1)
        picking_vals = self._prepare_internal_picking_vals(picking_type=picking_type,
                                                           location_id=location_id,
                                                           location_dest_id=dest_location_id,
                                                           group_id=group_id)
        picking = stock_picking_env.create(picking_vals)
        vals = self._prepare_stock_move_vals(product_id=product_id,
                                             qty=qty,
                                             location_id=location_id,
                                             location_dest_id=dest_location_id,
                                             picking_id=picking,
                                             group_id=group_id)
        picking.move_ids = [(0, 0, vals)]
        picking.move_ids.write({"location_id": location_id, "location_dest_id": dest_location_id,
                                "picking_type_id": picking.picking_type_id.id})
        picking.action_confirm()
        picking.do_unreserve_and_reserve_based_on_lot(lot_ids=lot_id)
        if picking.state == 'assigned':
            try:
                res = picking.with_context(is_custom_valuation=is_raw_material_product).button_validate()
            except Exception as e:
                _logger.error("Error {} comes at the time of validating picking {}".format(e, picking.name))
                return picking
            if res and isinstance(res, dict) and res.get(
                    'res_model') == 'stock.backorder.confirmation':
                wiz = Form(self.env[res['res_model']].with_context(res['context'])).save()
                wiz.with_context(is_custom_valuation=is_raw_material_product).process()
        return picking

    def get_location_wise_move(self, location_id=False):
        locations_ids = location_id or self.move_raw_ids.product_id.destination_location_id + self.location_src_id
        moves_data = {}
        product_ids = self.move_raw_ids.mapped('product_id')
        for location_id in locations_ids:
            if location_id.id == self.location_src_id:
                continue
            location_products = product_ids.filtered(lambda prod: prod.destination_location_id.id == location_id.id)
            need_to_process_move = self.move_raw_ids.filtered(lambda move: move.product_id.id in location_products._ids)
            if need_to_process_move:
                moves_data.update({location_id: need_to_process_move})
        return moves_data

    def is_src_contain_wip_stock_location(self):
        return True if self.product_id.source_location_id.is_wip_stock_location else False

    def action_return_component(self):
        return self.workorder_ids[0].action_return_component()

    def button_mark_done(self):
        """
        Added By : Ravi Kotadiya | On : Aug-24-2023
        Use : To avoid to show consumption warning while MO define with 0 quantity
        """
        res = super(MrpProduction, self).button_mark_done()
        if self.check_is_bom_with_zero_quantity():
            if res and isinstance(res, dict) and res.get('res_model') == 'mrp.consumption.warning':
                consumption_warning = Form(self.env['mrp.consumption.warning'].with_context(**res['context']))
                try:
                    res = consumption_warning.save().action_confirm()
                except Exception as e:
                    _logger.info(
                        "Error {} comes at the timg of confirming consumption wizard for mo {}:{}".format(e, self.id,
                                                                                                          self.name))
        return res

    def check_is_bom_with_zero_quantity(self):
        return bool(self.bom_id.bom_line_ids and sum(self.bom_id.bom_line_ids.mapped('product_qty')) == 0)

    def create_raw_material_movement(self, product_id, qty, location_id, location_dest_id,  lot_id):
        return self.env["setu.raw.material.movement"].create({'production_id': self.id,
                                                       'product_id': product_id.id,
                                                       'quantity': qty,
                                                       'location_id': location_id.id,
                                                       'location_dest_id': location_dest_id.id,
                                                       'lot_id': lot_id.id if lot_id else False,
                                                       })

    def get_available_component_qty_for_return(self):
        production_ids = self.procurement_group_id.mrp_production_ids
        return sum(
            production_ids.mapped('move_raw_ids').filtered(lambda move: move.state != 'done').mapped('quantity'))

    def action_add_product(self):
        return self.action_add_component()

    def action_add_component(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp_workorder.additional.product',
            'views': [
                [self.env.ref('production_planning.view_mrp_workorder_additional_product_wizard').id, 'form']],
            'name': _('Add Component'),
            'target': 'new',
            'context': {
                'production_id': self.id,
                'default_type': 'component',
                'product_ids': self.move_raw_ids.mapped('product_id').ids
            }
        }

    def raise_error_if_multiple_lot_found(self, lot_id=False):
        lot_ids = self.get_lot_from_move()
        lot_names = '\n'.join(lot_id.name for lot_id in lot_ids)
        if len(lot_ids) > 1:
            raise UserError(
                "Manufacturing Order {} contains given lots, lot should be single!\n{}".format(self.name,
                                                                                               lot_names))
        if lot_id and len(lot_ids) and lot_id.id not in lot_ids._ids:
            raise UserError(
                "You are trying to add another Lot, Please use given Lot first\n\n{}".format(lot_names))

    def get_lot_from_move(self):
        return self.move_raw_ids.filtered(
            lambda move: move.state != 'cancel').move_line_ids.mapped('lot_id')

    def return_product_to_stock(self, return_qty=0):
        lot_ids = self.get_lot_from_move()
        return_wiz = self.env['mrp_workorder.additional.product'].create(
            {
                'workorder_id': self.workorder_ids[:1].id,
                'is_return': True,
                'product_id': self.move_raw_ids[:1].product_id.id,
                'lot_id': lot_ids[:1].id,
                'product_qty': return_qty,
                'production_id': self.id
            }
        )
        return return_wiz.return_product()