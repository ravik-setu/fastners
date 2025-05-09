# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MrpProductionPlanning(models.Model):
    _name = 'mrp.production.planning.line'
    _description = "Production Planning Lines"
    _order = 'id desc'

    planning_id = fields.Many2one("mrp.production.planning", "Planning")
    product_id = fields.Many2one('product.product', 'Product')
    workcenter_id = fields.Many2one("mrp.workcenter", string="Machine")
    qty = fields.Float('Qty')
    available_qty = fields.Float("Available in KG")
    available_qty_in_pcs = fields.Float("Available in PCS")
    company_id = fields.Many2one(
        'res.company', 'Company', default=lambda self: self.env.company)
    bom_id = fields.Many2one(
        'mrp.bom', 'Bill of Material',
        domain="""[
            '|',
                ('product_id', '=', product_id),
                '&',
                    ('product_tmpl_id.product_variant_ids', '=', product_id),
                    ('product_id','=',False),
            ('type', '=', 'normal'),
            '|',
                ('company_id', '=', company_id),
                ('company_id', '=', False)
            ]""",
        check_company=True)
    mo_count = fields.Integer("Manufacturing Orders", compute='_compute_mo_count',store=True)
    done_qty = fields.Float(string="Quantity", compute='_compute_mo_count', store=True)
    pending_qty = fields.Float(string="Quantity", compute='_compute_mo_count',store=True)
    running_production_id = fields.Many2one("mrp.production", string="Running Production")
    state = fields.Selection(related="planning_id.state", store=True)
    in_progress = fields.Boolean(string="In Progress", copy=False)
    lot_name = fields.Char(string="Lot/Serial")
    reserved_qty = fields.Float(string='Reserved Qty', compute='_compute_mo_count',store=True)
    component_status = fields.Selection([
        ('available', 'Available'),
        ('unavailable', 'Not Available'),
        ('partially_available', 'Partially Available')], compute='_compute_component_status')
    subcontract_ids = fields.One2many('purchase.order', 'planning_lines_id', string='Subcontract')
    subcontract_bom_id = fields.Many2one('mrp.bom')

    @api.depends('planning_id.mo_ids', 'subcontract_ids')
    def _compute_mo_count(self):
        for rec in self:
            product_mos = rec.find_product_mos()
            rec.mo_count = len(product_mos)
            rec.done_qty = sum(product_mos.mapped('qty_produced')) + sum(rec.subcontract_ids.filtered(lambda sub: sub.state != 'cancel').order_line.mapped('product_qty'))
            rec.pending_qty = rec.qty - min(rec.done_qty, rec.qty)
            rec.reserved_qty = product_mos.get_available_component_qty_for_return()
            if not rec.pending_qty:
                rec.button_stop()

    def open_manufacturing_orders(self):
        action = self.env.ref('mrp.mrp_production_action').sudo().read()[0]
        action['domain'] = [('id', 'in', self.find_product_mos().ids)]
        return action

    def find_product_mos(self):
        return self.planning_id.mo_ids.filtered(lambda mo: mo.product_id.id == self.product_id.id)

    def action_add_product(self):
        return self.running_production_id.action_add_product()

    def action_register_production(self):
        if not self.running_production_id:
            raise UserError("No any production order found!")
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'register.daily.production',
            'views': [[self.env.ref('production_planning.default_register_daily_production_view_form').id, 'form']],
            'name': _('Register Production'),
            'target': 'new',
            'context': {
                'default_planning_id': self.planning_id.id,
                'default_planning_line': self.id,
                'default_production_id': self.running_production_id.id,
                'default_product_id': self.product_id.id,

            }
        }

    def button_start(self):
        self.in_progress = True
        self.running_production_id.workorder_ids.button_start() if self.running_production_id.workorder_ids else self.running_production_id.button_start_stop()

    def button_stop(self):
        self.in_progress = False
        self.running_production_id.workorder_ids.button_pending() if self.running_production_id.workorder_ids else self.running_production_id.button_start_stop()

    def find_latest_backorder(self):
        return self.running_production_id.procurement_group_id.mrp_production_ids.filtered(
            lambda mo: mo.state != 'done')[:1]

    def action_register_subcontract(self):
        subcontract_bom_id = self.env['mrp.production.planning'].find_bill_of_material(product_id=self.product_id, type='subcontract')
        if not subcontract_bom_id:
            raise UserError('Subcontract BOM is missing for this product!')
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'register.subcontract',
            'views': [[self.env.ref('production_planning.default_register_subcontract_view_form').id, 'form']],
            'name': _('Subcontract'),
            'target': 'new',
            'context': {
                'default_planning_id': self.planning_id.id,
                'default_planning_line': self.id,
                'default_production_id': self.running_production_id.id,
                'default_product_id': self.product_id.id,
                'default_bom_id': subcontract_bom_id.id,
            }
        }

    def _compute_component_status(self):
        for rec in self:
            bom_id = rec.bom_id
            if all(sum(self.env['stock.quant'].search(
                    [('product_id', '=', line.product_id.id),
                     ('location_id', '=', line.product_id.destination_location_id.id),
                     ('quantity', '>', 0)]).mapped('quantity')) >= (rec.pending_qty * line.product_qty) for line in bom_id.bom_line_ids):
                rec.component_status = 'available'
            elif any(sum(self.env['stock.quant'].search(
                    [('product_id', '=', line.product_id.id),
                     ('location_id', '=', line.product_id.destination_location_id.id),
                     ('quantity', '>', 0)]).mapped('quantity')) >= (rec.pending_qty * line.product_qty) for line in bom_id.bom_line_ids):
                rec.component_status = 'partially_available'
            else:
                rec.component_status = 'unavailable'
