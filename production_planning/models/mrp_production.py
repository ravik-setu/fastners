from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools.float_utils import float_round

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    planning_id = fields.Many2one('mrp.production.planning', copy=False)
    workcenter_id = fields.Many2one("mrp.workcenter", string="Machine")
    planning_lot_id = fields.Many2one("planning.lot", related="planning_id.lot_id", string="Planning Lot", store=True)
    in_progress= fields.Boolean(string="In Progress", default=False, copy=False)

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
            if vals.get('product_id') and not self.env.context.get('is_subcontract'):
                product = self.env["product.product"].browse(vals.get('product_id'))
                if product.destination_location_id:
                    vals.update({'location_dest_id': product.destination_location_id.id})
                if product.source_location_id:
                    vals.update({'location_src_id': product.source_location_id.id})
        res = super(MrpProduction, self).create(vals_list)
        for rec in res:
            if not self.env.context.get('is_subcontract') and not self.env.context.get('skip_confirm'):
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
                'img_url': '/web/static/src/img/smile.svg',
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
