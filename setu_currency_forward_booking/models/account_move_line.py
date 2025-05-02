from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    income_type = fields.Many2one('setu.bank.charges', string="Income Type")
