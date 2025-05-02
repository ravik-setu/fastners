# -*- coding: utf-8 -*-
from odoo import fields, models, _


class SetuBankCharges(models.Model):
    _name = 'setu.bank.charges'
    _description = "Setu Bank Charges"

    name = fields.Char(name="Charges")
    charges_type = fields.Selection(selection=[('expense', 'Expense'), ('income', 'Income')])
