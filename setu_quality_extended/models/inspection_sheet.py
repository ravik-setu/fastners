from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from datetime import date, datetime

class SetuQualityCheckSheet(models.Model):
    _name = "setu.quality.check.sheet"
    _inherit = ['mail.thread']
    _description = "Setu Quality Inspection Sheet"

    name = fields.Char()
    source = fields.Char(compute='_get_source', store=True,tracking=True)
    partner_id = fields.Many2one(
        'res.partner', string="Partner", compute='_get_source', store=True,tracking=True)
    product_id = fields.Many2one(
        'product.product', domain="[('id', 'in', available_product_ids)]",tracking=True)
    picking_id = fields.Many2one('stock.picking',tracking=True)
    production_id = fields.Many2one('mrp.production')
    lot_id = fields.Many2one('stock.lot',tracking=True)
    team_id = fields.Many2one('setu.quality.alert.team',tracking=True)
    company_id = fields.Many2one('res.company',tracking=True)
    quality_check_ids = fields.One2many(
        'setu.quality.check', 'inspection_sheet_id', store=True)
    date = fields.Date(default=fields.Date.today())
    # quantity_recieved = fields.Float(
    #     compute="_compute_quantity_received", string="Quantity Received", store=True)
    quantity_recieved = fields.Float(string="Quantity Received")
    quantity_accepted = fields.Float()
    quantity_rejected = fields.Float()
    quantity_pending = fields.Float()
    quantity_destructive = fields.Float()
    under_deviation = fields.Float()
    quality_inspector = fields.Many2many(
        'hr.employee', string='Quality Inspector', domain="[('id','in',quality_inspector_id)]")
    quality_inspector_id = fields.Many2many(
        related="team_id.quality_inspector")
    state = fields.Selection([('open', 'Open'),
                              ('accept', 'Approved'),
                              ('released','Released'),
                              ('reject', 'Rejected'), ('cancel', 'Cancelled')], default='open')
    processed = fields.Boolean()
    sampled_quantity = fields.Float()

    revised_sheet_ids = fields.One2many(
        'setu.quality.check.sheet.revision', 'inspection_sheet_id')
    code = fields.Selection([('incoming', 'Receipt'),
                            ('outgoing', 'Delivery'),
                            ('internal', 'Internal Transfer'),
                            ('mrp_operation', 'Manufacturing')], related="picking_id.picking_type_code")
    plan_id = fields.Many2one(
        'setu.quality.check.plan', compute="compute_inspection_plan", store=True)
    is_editable = fields.Boolean(compute="compute_is_editable")
    related_sheet_id = fields.Many2one(
        'setu.quality.check.sheet', string="Related Sheet", compute="compute_related_sheet", store=True)
    available_product_ids = fields.Many2many('stock.picking', compute='_compute_available_product_ids')
    warehouse_id = fields.Many2one('stock.warehouse',related='picking_id.picking_type_id.warehouse_id')

    def write(self,vals):
        if vals.get('quality_check_ids'):
            for val in vals.get('quality_check_ids'):
                if val[0] == 0 and not self.user_has_groups('setu_quality_extended.inspection_quality_check_access'):
                    raise UserError(_("""OOPS!!!\nLooks like you aren't authorized to add Quality Checks"""))
        return super(SetuQualityCheckSheet,self).write(vals)

    @api.depends('picking_id')
    def _compute_available_product_ids(self):
        for sheet in self:
            product_ids = []
            if sheet.picking_id:
                product_ids = sheet.picking_id.move_ids_without_package.mapped('product_id').ids
            sheet.available_product_ids = [(6, 0, product_ids)]

    @api.onchange('picking_id', 'product_id')
    def lot_id_filter(self):
        if self.picking_id and self.product_id:
            move_line_ids = self.picking_id.move_line_ids.filtered(
                lambda line: line.product_id == self.product_id)
            lot_ids = move_line_ids.mapped('lot_id')
            return {'domain': {'lot_id': [('id', 'in', lot_ids.ids)]}}
        else:
            return {'domain': {'lot_id': []}}

    @api.onchange('quantity_recieved', 'quantity_accepted', 'quantity_rejected', 'quantity_destructive', 'under_deviation')
    def onchange_quantity_validation(self):
        for rec in self:
            if self.quantity_accepted > (self.quantity_recieved + self.quantity_rejected + self.quantity_destructive + self.under_deviation + self.quantity_pending):
                raise UserError(
                    _(""" The Accepted Quantity should not be greater than the Received Qty, Rejected Qty, Destructive Qty,Pending Qty"""))

    def compute_is_editable(self):
        for rec in self:
            if rec.plan_id:
                rec.is_editable = True
            else:
                rec.is_editable = False

    @api.depends('picking_id', 'production_id')
    def compute_related_sheet(self):
        for rec in self:
            if rec.picking_id and rec.picking_id.backorder_id:
                sheet = self.env['setu.quality.check.sheet'].search(
                    [('picking_id', '=', rec.picking_id.backorder_id.id), ('product_id', '=', rec.product_id.id)], limit=1)
                rec.related_sheet_id = sheet.id if sheet else False

    @api.depends('production_id', 'picking_id', 'product_id')
    def compute_inspection_plan(self):
        for rec in self.filtered(lambda x: x.product_id):
            if rec.production_id and rec.production_id.picking_type_id and rec.product_id:
                plan = self.env['setu.quality.check.plan'].search([('picking_type_id', '=', rec.production_id.picking_type_id.id), (
                    'product_tmpl_id', '=', rec.product_id.product_tmpl_id.id)], limit=1)
                if plan and plan.filtered(lambda x: x.product_id and x.product_id == rec.product_id):
                    rec.plan_id = plan.filtered(
                        lambda x: x.product_id and x.product_id == rec.product_id).id if plan else False
                else:
                    rec.plan_id = plan.id if plan else False
            elif rec.picking_id and rec.picking_id.picking_type_id and rec.product_id:
                plan = self.env['setu.quality.check.plan'].search([('picking_type_id', '=', rec.picking_id.picking_type_id.id), (
                    'product_tmpl_id', '=', rec.product_id.product_tmpl_id.id)], limit=1)
                if plan and plan.filtered(lambda x: x.product_id and x.product_id == rec.product_id):
                    rec.plan_id = plan.filtered(
                        lambda x: x.product_id and x.product_id == rec.product_id).id if plan else False
                else:
                    rec.plan_id = plan.id if plan else False
            else:
                rec.plan_id = False

    @api.depends('picking_id', 'product_id')
    def _get_source(self):
        for rec in self:
            if rec.picking_id:
                rec.source = ''
                rec.partner_id = None
                purchase_id = rec.picking_id.move_ids_without_package.purchase_line_id.mapped('order_id')
                if purchase_id:
                    purchase_id = purchase_id[:1]
                    rec.partner_id = purchase_id.partner_id.id
                    rec.source = purchase_id.name
            elif rec.production_id:
                rec.source = rec.production_id.name
                rec.partner_id = None

    def state_approve(self):
        if self.env.user.id in self.team_id.approver_ids.ids:
            current_sates = self.quality_check_ids.mapped('quality_state')
            if 'none' in current_sates:
                raise UserError(
                    _("""OOPS!!!\nStill you need to do quality testing"""))
            else:
                self.state = 'accept'
                self.message_post(body="Approved")
        else:
            raise UserError("""OOPS!!!\nLooks like you aren't authorized to Approve""")
        receive = round(self.quantity_recieved, 2)
        val = round(self.quantity_accepted + self.quantity_rejected +
                    self.quantity_destructive + self.quantity_pending, 2)
        if val != receive:
            raise ValidationError(_("""Sum of Quantities (Accepeted, Rejected, Destructive) "MUST" be equal to Recieved Quantity"""))

        checks = self.env['setu.quality.check'].search([('picking_id', '=', self.picking_id.id),
                                                   ('production_id', '=',self.production_id.id),
                                                   ('inspection_sheet_id','!=', False),
                                                   ('quality_state', '=', 'none')])
        if not checks:
            for rec in self.env['setu.quality.check'].search([('picking_id', '=', self.picking_id.id), ('production_id', '=', self.production_id.id), ('inspection_sheet_id', '=', False)]):
                rec.unlink()

    def button_cancel(self):
        for sheet in self:
            sheet.write({'state':'cancel'})
            for check in sheet.quality_check_ids:
                check.write({'quality_state':'cancel'})

    def state_reject(self):
        if self.env.user.id in self.team_id.approver_ids.ids:
            current_sates = self.quality_check_ids.mapped('quality_state')
            if 'none' in current_sates:
                raise UserError(_("""OOPS!!!\nStill you need to do quality testing"""))
            else:
                self.state = 'cancel'
        else:
            raise UserError(_("""OOPS!!!\nLooks like you aren't authorized to Reject"""))

        val = round(self.quantity_accepted + self.quantity_rejected +
                    self.quantity_destructive + self.under_deviation, 1)
        receive = round(self.quantity_recieved, 1)
        if val != receive:
            raise ValidationError(
                _("""Sum of Quantities (Accepeted, Rejected, Destructive) "MUST" be equal to Recieved Quantity"""))

    @api.model
    def create(self, vals):
        sequence = self.env['stock.picking'].browse(vals.get('picking_id')).picking_type_id.sequence_for_inspection_sheet or \
            self.env['mrp.production'].browse(
                vals.get('production_id')).picking_type_id.sequence_for_inspection_sheet
        if sequence:
            vals['name'] = sequence.next_by_id()
        return super(SetuQualityCheckSheet, self).create(vals)

    def process_quantities(self):
        if self.picking_id:
            self.picking_id.qc_duplication_inp_sheet = True
            line = {
                'product_id': self.product_id.id,
                'location_dest_id': self.picking_id.location_dest_id.id,
                'product_uom_id': self.product_id.product_tmpl_id.uom_id.id,
                'location_id': self.picking_id.location_id.id,
                'lot_id': self.lot_id.id,
                'no_inspect': True
            }
            if self.quantity_accepted or self.under_deviation:
                line.update(
                    {'quantity': self.quantity_accepted+self.under_deviation})
                # self.picking_id.move_line_ids = [(0,0,line)]
                self.picking_id.move_line_ids = [(1, self.picking_id.move_line_ids.filtered(
                    lambda x:x.product_id == self.product_id and x.lot_id == self.lot_id).id, {'quantity': self.quantity_accepted+self.under_deviation})]
                self.picking_id.move_line_ids = [(1, self.picking_id.move_line_ids.filtered(
                    lambda x:x.product_id == self.product_id and x.lot_id == self.lot_id).id, {'quantity': self.quantity_accepted+self.under_deviation})]

            if self.quantity_rejected:
                warehouse_obj = self.picking_id.picking_type_id.warehouse_id
                dest = self.env['stock.location'].search(
                    [('warehouse1_id', '=', warehouse_obj.id), ('reject_location', '=', True)])
                if not dest:
                    raise UserError(_("Please set a Reject Location."))
                line.update({'quantity': self.quantity_rejected,
                            'location_dest_id': dest.id})
                self.picking_id.move_line_ids = [(0, 0, line)]

            if self.quantity_destructive:
                warehouse_obj = self.picking_id.picking_type_id.warehouse_id

                dest = self.env['stock.location'].search(
                    [('warehouse1_id', '=', warehouse_obj.id), ('destructive_location', '=', True)])
                if not dest:
                    raise UserError(_("Please set a Destructive Location1."))
                current_move_id = self.env['stock.move'].search(
                    [('picking_id', '=', self.picking_id.id), ('product_id', '=', self.product_id.id)])
                line.update({'quantity': self.quantity_destructive,
                            'location_dest_id': dest.id})
                current_move_id.location_dest_id = self.env['stock.location'].search(
                    [('warehouse1_id', '=', warehouse_obj.id), ('destructive_location', '=', True)]).id
                # line.move_id.update({'location_dest_id':self.env['stock.location'].search([('destructive_location','=',True)]).id})
                self.picking_id.move_line_ids = [(0, 0, line)]

        else:
            production = self.production_id
            quantity_accepted = self.quantity_accepted
            by_product_quantity = round(self.quantity_rejected + self.quantity_destructive + self.under_deviation + self.quantity_pending, 1)
            if by_product_quantity > 0:
                if not production.move_byproduct_ids:
                    raise ValidationError("By-Products Not Avialable in Manufacturing Order.")
                production.move_byproduct_ids.write({'product_uom_qty':by_product_quantity,'quantity_done':by_product_quantity})
                production.qty_producing = quantity_accepted
            else:
                production.qty_producing = quantity_accepted

        self.state = 'released'
        self.processed = True

    def revise(self):
        ids = []
        for line in self.quality_check_ids:
            ids.append(self.env['setu.quality.check.revision'].create({
                'point_id': line.point_id.id,
                'title': line.title,
                'test_type': line.test_type,
                'test_type_id': line.test_type_id.id,
                'test_method_id': line.test_method_id.id,
                'measure': line.measure,
                'norm': line.norm,
                'norm_unit': line.norm_unit,
                'tolerance_min': line.tolerance_min,
                'tolerance_max': line.tolerance_max,
                'quality_state': line.quality_state,
            }).id)

        revise_sheet = self.env['setu.quality.check.sheet.revision'].create({
            'name': self.name,
            'source': self.source,
            'product_id': self.product_id.id,
            'picking_id': self.picking_id.id,
            'production_id': self.production_id.id,
            'lot_id': self.lot_id.id,
            'team_id': self.team_id.id,
            'company_id': self.company_id.id,
            'date': self.date,
            'quantity_recieved': self.quantity_recieved,
            'quantity_accepted': self.quantity_accepted,
            'quantity_rejected': self.quantity_rejected,
            'quantity_destructive': self.quantity_destructive,
            'under_deviation': self.under_deviation,
            'status': self.status,
            'sampled_quantity': self.sampled_quantity,
            'quality_check_ids': [(6, 0, ids)],
        })

        self.revised_sheet_ids = [(4, revise_sheet.id, 0)]

        name = self.name.split('-')
        number = int(name[1]) if len(name) > 1 else 0
        name = name[0]

        self.name = name+'-'+str(number+1)
        self.state = 'open'

    @api.model
    def auto_revise(self):
        sheets = self.env['setu.quality.check.sheet'].search(
            ['|', ('production_id', '!=', False), ('picking_id', '!=', False), ('plan_id', '!=', False)])
        for sheet in sheets:
            if sheet.production_id and sheet.production_id.date_confirm and sheet.production_id.state in ['confirmed', 'progress', 'to_close']:
                if not sheet.production_id.set_interval and (sheet.plan_id.days or sheet.plan_id.hours or sheet.plan_id.minutes or sheet.plan_id.seconds):
                    sheet.production_id.date_confirm = sheet.production_id.date_confirm + \
                        relativedelta(days=sheet.plan_id.days, hours=sheet.plan_id.hours,
                                      minutes=sheet.plan_id.minutes, seconds=sheet.plan_id.seconds)
                    sheet.production_id.set_interval = True
                if sheet.production_id.set_interval and sheet.production_id.date_confirm <= datetime.now():
                    sheet.revise()
                    sheet.production_id.date_confirm = sheet.production_id.date_confirm + \
                        relativedelta(days=sheet.plan_id.days, hours=sheet.plan_id.hours,
                                      minutes=sheet.plan_id.minutes, seconds=sheet.plan_id.seconds)
            elif sheet.picking_id and sheet.picking_id.date_confirm and sheet.picking_id.state in ['draft', 'waiting', 'confirmed', 'assigned']:
                if not sheet.picking_id.set_interval and (sheet.plan_id.days or sheet.plan_id.hours or sheet.plan_id.minutes or sheet.plan_id.seconds):
                    sheet.picking_id.date_confirm = sheet.picking_id.date_confirm + \
                        relativedelta(days=sheet.plan_id.days, hours=sheet.plan_id.hours,
                                      minutes=sheet.plan_id.minutes, seconds=sheet.plan_id.seconds)
                    sheet.picking_id.set_interval = True
                if sheet.picking_id.set_interval and sheet.picking_id.date_confirm <= datetime.now():
                    sheet.revise()
                    sheet.picking_id.date_confirm = sheet.picking_id.date_confirm + \
                        relativedelta(days=sheet.plan_id.days, hours=sheet.plan_id.hours,
                                      minutes=sheet.plan_id.minutes, seconds=sheet.plan_id.seconds)
