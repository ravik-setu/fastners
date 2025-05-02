from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class SetuGateEntryRegister(models.Model):
    _name = "setu.gate.entry.register"
    _description = "setu gate entry register"
    _inherit = ['mail.thread']
    _order = "id desc"

    name = fields.Char(string="Name")
    un_visitor_reason = fields.Char(string="Reason")
    un_visitor_vehicle_no = fields.Char(string="Visitor Vehicle No.")
    reason = fields.Char(string="Description")
    visitor_name = fields.Char(string="Visitor Name")
    visitor_contact = fields.Char(string="Visitor's Mobile No.")
    visitor_email = fields.Char(string="Visitor's Email")
    visitor_company = fields.Char(string="Visitor's Company")
    visitor_vehicle_no = fields.Char(string="Visitor's Vehicle No.")

    un_visitor_count = fields.Integer(string="Total Visitors", default=1)

    invoice_weight = fields.Float(string="Weight")
    no_of_bags = fields.Float(string="No. of Bags")

    date = fields.Date(string="Date", default=fields.Datetime.now)
    in_time_visitor = fields.Datetime(string="In Time")
    out_time_visitor = fields.Datetime(string="Out Time")

    type = fields.Selection(selection=[('inward', 'Inward'), ('outward', 'Outward'),
                                       ('visitor', 'Visitor')], string="Type", default="inward")
    state = fields.Selection(selection=[('on_way', 'On way'), ('in', 'In'), ('out', 'Out'), ('cancel', 'Cancelled')],
                             string="State", default="on_way")

    person_to_meet_id = fields.Many2one(comodel_name="res.users", string="Appointee")
    product_id = fields.Many2one(comodel_name="product.product", string="Product")
    company_id = fields.Many2one(comodel_name="res.company", string="Company", default=lambda self: self.env.company.id)

    def in_button(self):
        if self.type == "inward":
            self.name = self.env['ir.sequence'].next_by_code('setu.entry.inward')
        if self.type == "outward":
            self.name = self.env['ir.sequence'].next_by_code('setu.entry.outward')
        if self.type == "visitor":
            self.name = self.env['ir.sequence'].next_by_code('setu.entry.visitor')
        self.write({'state': 'in',
                    'in_time_visitor': fields.Datetime.now()})

    def out_button(self):
        self.write({'state': 'out', 'out_time_visitor': fields.Datetime.now()})

    def cancel_button(self):
        self.write({'state': 'cancel'})

    @api.model
    def create(self, vals):
        if self.env.context.get('type') == 'visitor':
            vals['type'] = 'visitor'
        elif self.env.context.get('type') == 'outward':
            vals['type'] = 'outward'
        return super(SetuGateEntryRegister, self).create(vals)

    @api.constrains('in_time_visitor', 'out_time_visitor')
    def _check_end_date(self):
        if self.out_time_visitor and self.in_time_visitor and self.out_time_visitor < self.in_time_visitor:
            raise ValidationError(_('Out Time must be greater than In Time'))

    @api.onchange('visitor_contact')
    def _onchange_contact_number(self):
        if self.visitor_contact:
            existing_record = self.search([('visitor_contact', '=', self.visitor_contact)], limit=1)
            self.visitor_name = existing_record.visitor_name
            self.visitor_email = existing_record.visitor_email
            self.visitor_company = existing_record.visitor_company
            self.visitor_vehicle_no = existing_record.visitor_vehicle_no
