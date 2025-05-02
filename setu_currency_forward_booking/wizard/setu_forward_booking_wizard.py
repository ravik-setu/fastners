# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class SetuForwardBookingWizard(models.TransientModel):
    _name = 'setu.forward.booking.wizard'
    _description = "Setu Forward Booking Wizard"

    booking_amount = fields.Float(string="Booking Amount")
    remaining_amount = fields.Monetary(related='forward_booking_id.remaining_amount')
    register_payment_id = fields.Many2one(comodel_name='account.payment.register', string="Register Payment")
    forward_booking_id = fields.Many2one(comodel_name='setu.forward.booking', string="Forward Booking")
    currency_id = fields.Many2one(comodel_name='res.currency', string="Currency",
                                  related='register_payment_id.currency_id')
    company_id = fields.Many2one(related='register_payment_id.company_id', store=True)
    compute_booking_ids = fields.Many2many(comodel_name='setu.forward.booking', string="Reserved Bookings",
                                           compute="compute_reserved_booking")

    @api.depends('forward_booking_id')
    def compute_reserved_booking(self):
        """
            Author : Aastha Vora
            Date : 3rd July 2024
            Purpose : To compute booking ids for domain.
        """
        for rec in self:
            rec.compute_booking_ids = False
            move_id = rec.register_payment_id.env.context.get('active_id')
            order_id = self.env['account.move'].browse(move_id).invoice_line_ids.sale_line_ids.order_id
            booking_ids = self.env['setu.payment.schedule.lines'].search(
                [('order_id', '=', order_id.id)]).forward_booking_id
            rec.compute_booking_ids = booking_ids

    @api.onchange('booking_amount')
    def _onchange_booking_amount(self):
        """
            Author : Aastha Vora
            Date : 3rd July 2024
            Purpose : To delete payment schedule line from booking and remove booking record from payment schedule.
        """
        if self.booking_amount > self.remaining_amount:
            raise ValidationError(_("You Can not Enter Amount More Than the Remaining Amount."))
