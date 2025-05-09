from odoo import models, fields, api, _
import base64, math
from odoo.tools.misc import xlsxwriter
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES


class ProductionPlanning(models.Model):
    _name = 'mrp.production.planning'
    _description = "Production Planning"
    _order = 'id desc'


    name = fields.Char("Name", default=lambda x: _('New'), copy=False)
    order_date = fields.Date(string="Order Date")
    customer_id = fields.Many2one("res.partner", string="Customer")
    workcenter_id = fields.Many2one("mrp.workcenter", string="Machine Name")
    product_id = fields.Many2one("product.product", string="Product")
    product_tmpl_id = fields.Many2one("product.template", related="product_id.product_tmpl_id")
    standard_drawing = fields.Char("Standard/Drawing")
    marking = fields.Char(string="Marking")
    production_kg = fields.Float(string="Production Qty. Kg")
    rm_draw_size = fields.Char("")
    state = fields.Selection([
        ('draft', 'Draft'), ('confirm', 'Confirm'), ('in_progress', 'Inprogress'), ('done', 'Done'),
        ('cancel', 'Cancel')
    ], default='draft')
    priority = fields.Selection(
        PROCUREMENT_PRIORITIES, string='Priority', default='0',
        help="Planing will process first with the highest priorities.")
    company_id = fields.Many2one(
        'res.company', 'Company', default=lambda self: self.env.company,
        index=True, required=True)
    surface_finish = fields.Char(string="Surface Finish")
    mo_ids = fields.One2many("mrp.production", "planning_id", "Manufacturing Orders")
    planning_lines = fields.One2many("mrp.production.planning.line", "planning_id", string="Lines")
    qty = fields.Float(string="Quantity")
    lot_id = fields.Many2one("planning.lot", string="Serial Number/ Lot", copy=False)
    available_qty = fields.Float(string="Available Qty", compute='compute_available_qty')
    lot_name = fields.Char(string='Serial Number / Lot', copy=False)
    excel_file_data = fields.Binary()
    sale_order_ids = fields.Many2many("sale.order", "planing_id", "sale_id", string="Sale Orders")
    subcontract_ids = fields.One2many('purchase.order', 'planning_id', string='Subcontracts')

    def action_confirm(self):
        """
        Added By : Ravi Kotadiya | On : Apr-14-2023 | Task : 2114
        Use : To find the child bom and create lines with child boms
        """
        self.ensure_one()
        self.planning_lines.unlink()
        lst = []
        bom_id = self.find_bill_of_material(self.product_id.put_in_pack_product_id or self.product_id)
        if not bom_id:
            raise UserError(
                "No Bill of Material found for product {}".format(self.product_id.put_in_pack_product_id.name or self.product_id.name))
        line_product_ids = []
        bom_ids = self.find_all_mo_type_bom(bom_id)
        for bom_id in bom_ids:
            if bom_id.type == 'packaging':
                continue
            product_id = bom_id.product_id or bom_id.product_tmpl_id.product_variant_ids[0]
            qty = bom_ids.get(bom_id)
            if product_id.id == self.product_id.put_in_pack_product_id.id:
                available_qty = sum(
                    self.get_available_qty_on_location(self.product_id, find_quant=True).mapped('quantity'))
            else:
                available_qty = self.get_available_qty_on_location(product_id)
            if product_id and product_id not in line_product_ids:
                subcontract_bom_id = self.find_bill_of_material(product_id, type='subcontract')
                lst.append((0, 0, {'product_id': product_id.id, 'bom_id': bom_id.id,
                                   'available_qty': available_qty, 'qty': qty, 'subcontract_bom_id': subcontract_bom_id.id}))
                line_product_ids.append(bom_id.product_id.id)
        if lst:
            self.write({'planning_lines': lst, 'state': 'confirm'})

    def finish_planning(self):
        for rec in self:
            inprogress_mos = rec.mo_ids.filtered(lambda x: x.state not in ['done', 'cancel'])
            inprogress_mos.action_cancel()
            rec.planning_lines.button_stop()
            self.state = 'done'

    def find_bill_of_material(self, product_id=False, type=False):
        domain = ['|', ('product_id', '=', product_id.id), ('product_tmpl_id', '=', product_id.product_tmpl_id.id)]
        domain.append(('type', '=', type)) if type else (('type', '!=', 'phantom'))
        return self.env["mrp.bom"].search(domain, limit=1)

    def find_all_mo_type_bom(self, bom_id):
        """
        Purpose: To find all the child boms of normal type and also set the quantity to be produced based on the plan.
        """
        bom_ids = {}
        previous_qty = 0
        for line in bom_id.bom_line_ids:
            first_bom_id = self.find_bill_of_material(product_id=line.product_id, type='normal') or self.find_bill_of_material(product_id=line.product_id)
            if not first_bom_id:
                bom_ids.update({bom_id: bom_id.product_qty * self.qty})
                return bom_ids
            if first_bom_id:
                bom_ids.update({bom_id: (line.product_qty / line.bom_id.product_qty) * self.production_kg})
                previous_qty = line.product_qty * self.production_kg

        child_lines = bom_id.bom_line_ids
        while (child_lines):
            for line in child_lines:
                bill_of_material_ids = self.find_bill_of_material(product_id=line.product_id, type='normal') or self.find_bill_of_material(product_id=line.product_id)
                for bom_id in bill_of_material_ids:
                    bom_ids.update({bom_id: (line.product_qty / line.bom_id.product_qty) * previous_qty})
                    previous_qty *= (line.product_qty / line.bom_id.product_qty)
                child_lines += bom_id.bom_line_ids
                child_lines -= line
        return bom_ids

    def action_create_mo(self):
        """
        Added By : Ravi Kotadiya | On : Apr-14-2023 | Task : 2114
        Use : To create manufacturing order based on the planning lines
        """
        mrp_obj = self.env['mrp.production']
        lines = self.planning_lines.filtered(lambda line: line.qty > 0 and not line.product_id.id == self.product_id.id)
        if not lines and self.product_id.put_in_pack_product_id:
            raise UserError("Please Add Quantity into lines!")
        self.state = 'in_progress'
        for line in self.planning_lines.filtered(lambda line: line.qty > 0 and line.bom_id.type != 'subcontract'):
            vals = {'product_id': line.product_id.id,
                    'planning_id': self.id,
                    'product_tmpl_id': line.product_id.product_tmpl_id.id,
                    'product_uom_id': line.product_id.uom_id.id,
                    'product_qty': line.qty,
                    'bom_id': line.bom_id.id,
                    'workcenter_id': line.workcenter_id.id}
            try:
                mo_id = mrp_obj.create(vals)
                mo_id._compute_workorder_ids()
                if line.workcenter_id:
                    mo_id.workorder_ids.write({'workcenter_id': line.workcenter_id.id})
                mo_id.action_confirm()
                _logger.info(
                    "MO {}: {} created for planing{}:{} with Qty: {}".format(mo_id.id, mo_id.name, self.id, self.name,
                                                                             line.qty))
                line.write(
                    {'running_production_id': mo_id.id, 'workcenter_id': mo_id.workorder_ids[:1].workcenter_id.id})
            except Exception as e:
                _logger.info(
                    "Error {} comes at the time of creating MO for product {} Qty and planing {}".format(e,
                                                                                                         line.product_id.name,
                                                                                                         line.qty,
                                                                                                         self.name))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'name' not in vals or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('mrp.production.planning') or ''
        res = super(ProductionPlanning, self).create(vals_list)
        return res

    def cancel_planning(self):
        """
        Added By : Ravi Kotadiya | On : Apr-14-2023 | Task : 2114
        Use: Cancel Planning and related manufacturing orders
        """
        for rec in self:
            mo_ids = rec.mo_ids.filtered(lambda mo: mo.state != 'cancel' and mo.mrp_production_backorder_count > 1)
            if mo_ids:
                raise UserError(
                    _('Sorry you can not cancel Planning given manufacturing order is processed {}'.format(
                        '\n'.join(mo.name for mo in mo_ids))))
            rec.mo_ids.action_cancel()
            rec.planning_lines.button_stop()
            rec.state = 'cancel'

    def get_available_qty_on_location(self, product_id, location_id=False, find_quant=False):
        if hasattr(self.env["product.product"], 'destination_location_id'):
            location_id = location_id or product_id.destination_location_id
        quants = self.env["stock.quant"]._gather(product_id, location_id)
        if find_quant:
            return quants
        return sum(quants.mapped('available_quantity'))

    def get_lines_available_qty(self):
        for rec in self.planning_lines:
            if rec.product_id.id == rec.planning_id.product_id.put_in_pack_product_id.id:
                quants = self.get_available_qty_on_location(rec.product_id, find_quant=True)
                rec.available_qty = sum(quants.mapped('quantity'))
                rec.available_qty_in_pcs = sum(quants.mapped('quantity')) * rec.product_id.weight
            else:
                rec.available_qty = self.get_available_qty_on_location(rec.product_id)

    def action_generate_serial(self):
        if not self.lot_name:
            raise UserError("Please fill Serial/Lot for planning!")
        else:
            self.lot_id = self.env["planning.lot"].search([('name', '=', self.lot_name)])
            if not self.lot_id:
                self.lot_id = self.env["planning.lot"].action_generate_serial(self)
                self.lot_id.name = self.lot_name

    @api.onchange('product_id')
    def compute_available_qty(self):
        for rec in self:
            rec.available_qty = rec.get_total_available_qty()

    @api.onchange('qty')
    def onchange_qty(self):
        for rec in self:
            if rec.product_id.put_in_pack_product_id and rec.qty:
                rec.production_kg = rec.qty * rec.product_id.weight
            else:
                rec.production_kg = rec.qty

    def get_total_available_qty(self):
        qty = self.get_available_qty_on_location(self.product_id)
        if self.product_id.id != self.product_id.put_in_pack_product_id.id:
            available_qty = self.get_available_qty_on_location(self.product_id.put_in_pack_product_id)
            if self.product_id.uom_id.category_id.id != self.product_id.put_in_pack_product_id.uom_id.category_id.id:
                available_qty = available_qty * self.product_id.weight
            qty += available_qty
        return math.ceil(qty)

    def find_all_bom(self, bom_id):
        bom_ids = bom_id
        child_lines = bom_id.bom_line_ids
        while (child_lines):
            for line in child_lines:
                bom_id = self.find_bill_of_material(line.product_id)
                if bom_id:
                    bom_ids += bom_id
                    child_lines += bom_id.bom_line_ids
                child_lines -= line
        return bom_ids

    @api.onchange("sale_order_ids", "product_id")
    def onchange_sale_order_ids(self):
        for rec in self:
            lines = self.sale_order_ids.order_line.filtered(lambda line:line.product_id.id == self.product_id.id)
            rec.qty = sum(lines.mapped('product_uom_qty')) - sum(lines.mapped('qty_delivered'))

    def action_view_subcontracts(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Subcontracts',
            'view_mode': 'tree,form',
            'res_model': 'purchase.order',
            'domain': [('planning_id', '=', self.id)],
            'context': {'create': False}
        }

    def action_view_mos(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Manufacturing Orders',
            'view_mode': 'tree,form',
            'res_model': 'mrp.production',
            'domain': [('id', 'in', self.mo_ids.ids)],
            'context': {'create': False}
        }

    def button_start(self):
        self.planning_lines.button_start()

    def button_stop(self):
        self.planning_lines.button_stop()