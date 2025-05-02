# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime


class SetuPaymentSchedule(models.Model):
    _name = 'setu.payment.schedule'
    _description = "Setu Payment Schedule"

    name = fields.Char(string="Name")
    payment_date = fields.Date(string="Payment Date")
    amount = fields.Float(string="Amount")
    currency_id = fields.Many2one(comodel_name="res.currency", string="Currency")
    company_id = fields.Many2one(comodel_name="res.company", string="Company")
    order_id = fields.Many2one(comodel_name="sale.order", string="Sale Order")
    picking_id = fields.Many2one(comodel_name="stock.picking", string="Delivery")
    forward_booking_ids = fields.Many2many(comodel_name="setu.forward.booking", string="Booking")
    amount_in_inr = fields.Float(string="Amount In INR", compute="_get_amount_in_inr", store=True)
    payment_schedule_line_ids = fields.One2many('setu.payment.schedule.lines', 'payment_schedule_id',
                                                string="Payment Schedule Lines",
                                                domain="[('forward_booking_id', 'in', forward_booking_ids)]")
    remaining_amount = fields.Float(String="Remaining Amount", default=0.0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            name = self.env['ir.sequence'].next_by_code('setu.payment.schedule') or _("New")
            vals.update({'name': name})
        return super(SetuPaymentSchedule, self).create(vals_list)

    @api.depends("order_id", "order_id.order_booking_rate", "amount")
    def _get_amount_in_inr(self):
        for rec in self:
            amount_in_inr = 0
            if rec.order_id and rec.order_id.order_booking_rate > 0:
                amount_in_inr = rec.amount * rec.order_id.order_booking_rate
            rec.amount_in_inr = amount_in_inr

    def action_open_payment_schedule_wizard(self):
        total_remaining_amount = sum(
            [schedule.remaining_amount or schedule.amount for schedule in self.env['setu.payment.schedule'].search(
                [('id', 'in', self._context.get('active_ids')), ('remaining_amount', '>', 0),
                 '|', ('forward_booking_ids', '=', False), ('forward_booking_ids', '!=', False)])])
        wizard = self.env['setu.payment.schedule.booking.wizard'].create(
            {'total_remaining_amount': total_remaining_amount})
        wizard._onchange_total_remaining_amt()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payment Schedule Booking',
            'res_model': 'setu.payment.schedule.booking.wizard',
            'target': 'new',
            'views': [
                (self.env.ref('setu_currency_forward_booking.setu_payment_schedule_booking_wizard_form_view').id,
                 'form')],
            'res_id': wizard.id
        }
