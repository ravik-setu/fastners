# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class SetuBankChargesDetails(models.Model):
    _name = "setu.bank.received.amount.details"
    _description = "Setu Bank Received Amount Details"

    received_amount = fields.Float(string="Received Amount")
    payment_received_date = fields.Date(string="Payment Received Date")
    order_booking_rate = fields.Monetary(string="Order Booking rate", currency_field='company_currency_id')
    received_amount_in_currency = fields.Monetary(compute='_get_total_received_amount', string='Order Booking Amount',
                                                  currency_field='company_currency_id', store=True)
    hash_rate = fields.Monetary(string="Hashing rate", related="forward_booking_id.hash_rate",
                                currency_field='company_currency_id')
    hashing_amount = fields.Monetary(string="Hashing Amount", compute="_get_total_received_amount", compute_sudo=True,
                                     currency_field='company_currency_id')
    payment_id = fields.Many2one(comodel_name='account.payment', string='Payment')
    state = fields.Selection(related='payment_id.state', string="State")
    currency_id = fields.Many2one(comodel_name='res.currency', string="Currency")
    forward_booking_id = fields.Many2one(comodel_name='setu.forward.booking', string='Forward Booking')
    company_currency_id = fields.Many2one(related='forward_booking_id.company_currency_id')
    order_id = fields.Many2one(comodel_name='sale.order',string="Sale Order")

    @api.depends('received_amount', 'order_booking_rate', 'forward_booking_id.hash_rate', 'hash_rate')
    def _get_total_received_amount(self):
        """
            Author : Aastha Vora
            Date : 3rd July 2024
            Purpose : This method is used to get total received amount.
        """
        for rec in self:
            rec.received_amount_in_currency = rec.received_amount * rec.order_booking_rate
            rec.hashing_amount = rec.received_amount * rec.hash_rate
            order_id = rec.sudo().payment_id.reconciled_invoice_ids.invoice_line_ids.sale_line_ids.order_id
            if order_id:
                schedule_lines = self.sudo().forward_booking_id.payment_schedule_line_ids.filtered(
                    lambda x: x.order_id == order_id)
                for line in schedule_lines:
                    line.is_payment_received = True
