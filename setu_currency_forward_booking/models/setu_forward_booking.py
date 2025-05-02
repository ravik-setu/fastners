# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class SetuForwardBooking(models.Model):

    def _get_currency(self):
        return self.env.company.currency_id.search([('id', '!=', self.env.company.currency_id.id)])

    _name = "setu.forward.booking"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Forward Booking"
    _order = "id desc"

    name = fields.Char(string="Name", default=lambda self: _('New'))
    deal_date = fields.Date(string="Deal Date", default=fields.Datetime.now)
    start_date = fields.Date(string="Start Date", tracking=True)
    end_date = fields.Date(string="End Date", tracking=True)
    hash_rate = fields.Monetary(string="Hash Rate", currency_field='company_currency_id', tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('close', 'Close'),
        ('cancelled', 'Cancelled'),
    ], string="State", default="draft", tracking=True)

    currency_id = fields.Many2one(comodel_name="res.currency", string="Currency", tracking=True,
                                  default=lambda self: self._get_currency())
    bank_id = fields.Many2one(comodel_name="res.bank", string="Bank", tracking=True)
    bank_charges_details_ids = fields.One2many(comodel_name="setu.bank.charges.details",
                                               inverse_name='forward_booking_id', string="Order Details")
    bank_incoming_details_ids = fields.One2many(comodel_name="setu.bank.income.details",
                                                inverse_name='forward_booking_id', string="Order Details")
    payment_schedule_ids = fields.Many2many(comodel_name="setu.payment.schedule",
                                            relation='payment_schedule_rel', column1='forward_booking_id',
                                            column2='payment_schedule_id', string="Payment Schedule")

    bank_received_amount_ids = fields.One2many(comodel_name="setu.bank.received.amount.details",
                                               inverse_name='forward_booking_id', string="Payment Received Details")
    booking_amount = fields.Float(string="Booking Amount", currency_field='currency_id')
    remaining_amount = fields.Monetary(string="Remaining Amount",
                                       help="Total Booking Amount - Received Amount",
                                       compute="_compute_remaining_amount_and_cancellation_pnl",
                                       store=True, currency_field='currency_id')
    profit_or_loss = fields.Monetary(string="Profit or Loss", compute="_compute_profit_or_loss_amount",
                                     currency_field='company_currency_id', store=True,
                                     help="((Booking Amount - Remaining Amount) * Hash Rate) + Bank Income - Bank Charges - Total "
                                          "Received Amount + Cancellation Profit or Loss")
    cancellation_rate = fields.Monetary(string="Cancellation Rate", currency_field='company_currency_id')
    cancellation_profit_or_loss = fields.Monetary(string="Cancellation Profit or Loss Amount",
                                                  help="Remaining Amount * (Hashing Rate-Cancellation Rate)",
                                                  compute="_compute_remaining_amount_and_cancellation_pnl", store=True,
                                                  currency_field='company_currency_id')
    company_id = fields.Many2one(comodel_name="res.company", string="Company", default=lambda self: self.env.company)
    company_currency_id = fields.Many2one(related='company_id.currency_id', string="Company Currency")
    order_ids = fields.Many2many(comodel_name="sale.order", relation='sale_order_rel', column1='forward_booking_id',
                                 column2='order_id', string="Sale Orders")
    remarks = fields.Text(string="Remarks")
    received_amount = fields.Monetary(string="Received Amount",
                                      compute="_compute_remaining_amount_and_cancellation_pnl",
                                      store=True, currency_field='currency_id')
    payment_schedule_line_ids = fields.One2many(comodel_name="setu.payment.schedule.lines", inverse_name="forward_booking_id")

    @api.depends('start_date', 'end_date')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.name} - From {rec.start_date} To {rec.end_date}" if rec.start_date and rec.end_date else f"{rec.name}"
            if rec.end_date < rec.start_date:
                raise ValidationError(_("You can not set End Date prior than Start Date."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            name = self.env['ir.sequence'].next_by_code('setu.forward.booking') or _("New")
            vals.update({'name': name})
        return super(SetuForwardBooking, self).create(vals_list)

    @api.depends('hash_rate', 'cancellation_rate', 'remaining_amount', 'bank_received_amount_ids.received_amount',
                 'booking_amount')
    def _compute_remaining_amount_and_cancellation_pnl(self):
        """
            Author : Aastha Vora
            Date : 3rd July 2024
            Purpose : This method is used to compute Cancellation P&L and remaining amount.
        """
        for rec in self:
            rec.remaining_amount = 0
            rec.cancellation_profit_or_loss = 0
            received_amount = sum(rec.mapped('bank_received_amount_ids').mapped('received_amount'))
            rec.received_amount = received_amount
            if rec.booking_amount < received_amount:
                rec.remaining_amount = 0
            else:
                rec.remaining_amount = rec.booking_amount - received_amount
            if rec.cancellation_rate:
                rec.cancellation_profit_or_loss = (rec.cancellation_rate - rec.hash_rate) * rec.remaining_amount

    @api.depends('hash_rate', 'booking_amount', 'cancellation_rate', 'remaining_amount', 'bank_incoming_details_ids',
                 'bank_charges_details_ids')
    def _compute_profit_or_loss_amount(self):
        """
            Author : Aastha Vora
            Date : 3rd July 2024
            Purpose : This method is used to compute Profit or Loss Amount.
        """
        for rec in self:
            rec.profit_or_loss = 0
            bank_income = sum(rec.bank_incoming_details_ids.mapped('amount'))
            bank_charges = sum(rec.bank_charges_details_ids.mapped('charge_amount'))
            hashing_amount = (rec.booking_amount - rec.remaining_amount) * rec.hash_rate
            received_booking_amount = sum(rec.mapped('bank_received_amount_ids').mapped('received_amount_in_currency'))

            hashing_net_gross_amount = ((
                                                    hashing_amount + bank_income) - bank_charges) - received_booking_amount + rec.cancellation_profit_or_loss
            rec.profit_or_loss = hashing_net_gross_amount

    @api.onchange('payment_schedule_ids')
    def _onchange_payment_schedule_ids_set_booking_id(self):
        for rec in self.payment_schedule_ids:
            rec.forward_booking_ids = [(4, self.id)]

    def action_confirm(self):
        if not self.booking_amount:
            raise ValidationError("Booking Amount Should be Greater Than 0.")
        if not self.hash_rate:
            raise ValidationError("Hash Rate Should be Greater Than 0.")
        self.state = 'running'

    def action_cancel(self):
        if self.cancellation_rate <= 0:
            raise ValidationError("Cancellation Rate Must Be Greater Than 0.")
        self.state = 'cancelled'

    def action_close(self):
        self.state = 'close'
