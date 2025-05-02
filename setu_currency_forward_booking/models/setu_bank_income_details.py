# -*- coding: utf-8 -*-
from odoo import fields, models, _


class SetuBankIncomeChargesDetails(models.Model):
    _name = "setu.bank.income.details"
    _description = "Setu Bank Income Details"

    amount = fields.Monetary(string="Amount", currency_field='company_currency_id')
    charge_id = fields.Many2one(comodel_name="setu.bank.charges", string="Charges")
    company_currency_id = fields.Many2one(related='forward_booking_id.company_currency_id')
    forward_booking_id = fields.Many2one(comodel_name="setu.forward.booking", string="Forward Booking")
