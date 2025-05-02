# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    bank_income = fields.Boolean(string="Bank Income", copy=False)
    order_booking_rate = fields.Float(string="Order Booking Rate", tracking=True)
    forward_booking_ids = fields.Many2many('setu.forward.booking', 'journal_foraward_booking_rel', 'journal_id',
                                           'forward_booking_id',
                                           string="Forward Booking")


    def action_register_payment(self):
        res = super(AccountMove, self).action_register_payment()
        res['context'].update({'move_type': self.move_type})
        return res
