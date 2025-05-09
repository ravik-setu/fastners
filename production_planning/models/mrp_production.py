from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools.float_utils import float_round
from odoo.tests import Form

import logging
_logger = logging.getLogger(__name__)

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    planning_id = fields.Many2one('mrp.production.planning', copy=False)
    workcenter_id = fields.Many2one("mrp.workcenter", string="Machine")
    planning_lot_id = fields.Many2one("planning.lot", related="planning_id.lot_id", string="Planning Lot", store=True)
    in_progress= fields.Boolean(string="In Progress", default=False, copy=False)
    is_bom_component_available = fields.Boolean(compute="_compute_is_bom_component_available")

    def write(self, vals):
        """
        Added By : Ravi Kotadiya | On : Apr-14-2023 | Task : 2114
        Use : To change machine into running workorders
        """
        res = super(MrpProduction, self).write(vals)
        if vals.get('workcenter_id'):
            for mo in self.filtered(lambda mo: mo.workorder_ids):
                Query = "update mrp_workorder set workcenter_id={} where {}".format(
                    mo.workcenter_id.id,
                    "id={}".format(mo.workorder_ids.id) if len(mo.workorder_ids) == 1 else "id in {}".format(
                        mo.workorder_ids._ids))
                self._cr.execute(Query)
        return res

    @api.onchange('location_dest_id', 'move_finished_ids', 'bom_id')
    def _onchange_location_dest(self):
        destination_location = self.location_dest_id
        update_value_list = []
        for move in self.move_finished_ids:
            update_value_list += [(1, move.id, ({
                'warehouse_id': destination_location.warehouse_id.id,
                'location_dest_id': destination_location.id,
            }))]
        self.move_finished_ids = update_value_list

    @api.onchange('location_src_id', 'move_raw_ids', 'bom_id')
    def _onchange_location(self):
        source_location = self.location_src_id
        self.move_raw_ids.update({
            'warehouse_id': source_location.warehouse_id.id,
            'location_id': source_location.id,
        })

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('product_id') and not vals.get('subcontractor_id'):
                product = self.env["product.product"].browse(vals.get('product_id'))
                if product.destination_location_id:
                    vals.update({'location_dest_id': product.destination_location_id.id})
                if product.source_location_id:
                    vals.update({'location_src_id': product.source_location_id.id})
        res = super(MrpProduction, self).create(vals_list)
        for rec in res:
            if not vals.get('subcontractor_id') and not self.env.context.get('skip_confirm'):
                if rec.product_id.destination_location_id:
                    rec._onchange_location_dest()
                if rec.product_id.source_location_id:
                    rec._onchange_location()
            production_ids = res.procurement_group_id.mrp_production_ids
            if rec.picking_type_id.use_parent_mo_lot and production_ids:
                res.write({'lot_producing_id': production_ids[:1].lot_producing_id.id})
        return res

    def button_start_stop(self):
        operation_context = self._context.get('button_operation')
        for mo in self.filtered(lambda mo: mo.state not in ["done", "cancel"]):
            if mo.state not in 'done':
                if not operation_context:
                    mo.in_progress = not mo.in_progress
                    if mo.in_progress:
                        mo.workorder_ids.with_context(from_mo=True).button_start()
                    else:
                        mo.workorder_ids.with_context(from_mo=True).button_pending()
                elif operation_context == 'start':
                    mo.in_progress = True
                    mo.workorder_ids.with_context(from_mo=True).button_start()
                elif operation_context == 'stop':
                    mo.in_progress = False
                    mo.workorder_ids.with_context(from_mo=True).button_pending()

    def raise_error_another_mo_is_running(self, workcenter_id=False):
        workcenter_ids = self.workorder_ids.workcenter_id if not workcenter_id else workcenter_id
        production_ids = self.search([('workcenter_id', 'in', workcenter_ids._ids)])
        if production_ids:
            raise ValidationError(_(f"""Manufacturing order {production_ids.mapped('name')} is in process."""))

    def mark_done_and_create_backorder_if_needed(self):
        raw_material_product = self.bom_id.bom_line_ids.mapped("product_id").filtered(
            lambda prod: prod.is_raw_material)
        if raw_material_product:
            self.consumption = 'flexible'
        try:
            warning_action = self.button_mark_done()
        except Exception as e:
            raise UserError(e)
        if not isinstance(warning_action, bool) and warning_action.get('res_model') == 'user':
            return warning_action
        if not isinstance(warning_action, bool):
            if warning_action.get('res_model') == 'mrp.consumption.warning':
                context_data = warning_action.get('context')
                warning = self.env['mrp.consumption.warning'].with_context(context_data). \
                    create({'mrp_production_ids': context_data.get('default_mrp_production_ids'),
                            'mrp_consumption_warning_line_ids': context_data.get(
                                'default_mrp_consumption_warning_line_ids')
                            })
                warning_action = warning.action_set_qty()
            if not isinstance(warning_action, bool):
                warning_context = warning_action.get('context')
                backorder = self.env['mrp.production.backorder'].with_context(warning_context). \
                    create({'mrp_production_backorder_line_ids': warning_context.get(
                    'default_mrp_production_backorder_line_ids'),
                    'mrp_production_ids': warning_context.get('default_mrp_production_ids')
                })
                backorder.action_backorder()
                backorders = self.procurement_group_id.mrp_production_ids
                self.button_start_stop()
                backorders[-1].button_start_stop()
        return {
            'effect': {
                'fadeout': 'slow',
                'message': "Production Book Successfully",
                'img_url': '/web/static/img/smile.svg',
                'type': 'rainbow_man',
            }
        }

    def product_move_to_scrap(self, scrap_qty, lot_id):
        product = self.move_raw_ids[:1].product_id
        try:
            scrap = self.env['stock.scrap'].create({
                'product_id': product.id,
                'product_uom_id': product.uom_id.id,
                'scrap_qty': scrap_qty,
                'production_id': self.id,
                'lot_id': lot_id.id if lot_id else False,
                'location_id': self.location_src_id.id
            })
            scrap.do_scrap()
            self.create_raw_material_movement(product, scrap_qty,
                                              self.location_dest_id, self.location_src_id, lot_id)
        except Exception as e:
            raise UserError(
                _("ERROR : Error comes from validate reject : Product: {} ; with error : {}".format(
                    (product.id, product.name), e)))

    def _cal_price(self, consumed_moves):
        """Set a price unit on the finished move according to `consumed_moves`.
        """
        super(MrpProduction, self)._cal_price(consumed_moves)
        finished_move = self.move_finished_ids.filtered(
            lambda x: x.product_id == self.product_id and x.state not in ('done', 'cancel') and x.quantity)
        if finished_move:
            finished_move.ensure_one()
            if finished_move.product_id.cost_method in ('fifo', 'average'):
                finished_move.price_unit = finished_move.price_unit + finished_move.product_id.production_cost + self._cal_scrap_cost(
                    finished_move)
        return True

    def _cal_scrap_cost(self, finished_move):
        byproduct_cost_share = 0
        for byproduct in self.move_byproduct_ids.filtered(
                lambda m: m.state not in ('done', 'cancel') and m.quantity):
            if byproduct.cost_share == 0:
                continue
            byproduct_cost_share += byproduct.cost_share
        return -sum(self.scrap_ids.move_ids.sudo().stock_valuation_layer_ids.mapped('value')) * float_round(
            1 - byproduct_cost_share / 100, precision_rounding=0.0001) / finished_move.product_uom._compute_quantity(
            finished_move.quantity, finished_move.product_id.uom_id)

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
        if not self:
            raise UserError("No any production order found!")
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
                'product_ids': self.move_raw_ids.mapped('product_id').ids,
                'default_product_id': self.move_raw_ids.mapped('product_id')[:1].id
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
