from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class PaymentScheduleBookingLine(models.TransientModel):
    _name = "setu.payment.schedule.booking.line.wizard"
    _description = "Setu Payment Schedule Booking Line Wizard"

    booking_amount = fields.Float(string="Amount To Book")
    remaining_amount = fields.Float(string="Remaining Amount")
    payment_date = fields.Date(string="Payment Date")
    payment_schedule_id = fields.Many2one(comodel_name='setu.payment.schedule', string="Payment Schedule")
    currency_id = fields.Many2one(comodel_name="res.currency", string="Currency")
    booking_wizard_id = fields.Many2one(comodel_name="setu.payment.schedule.booking.wizard", string="Booking Wizard")
    company_id = fields.Many2one(comodel_name="res.company", string="Company")
    order_id = fields.Many2one(comodel_name="sale.order", string="Sale Order")

    @api.onchange('booking_amount')
    def _onchange_booking_amount(self):
        """
            Author : Aastha Vora
            Date : 3rd July 2024
            Purpose : This method is used to get remaining amount and check remaining amount must not greater than booking amount.
        """
        if self.booking_amount > self.payment_schedule_id.remaining_amount:
            raise ValidationError(_("You Can not Enter Amount More Than the Remaining Amount."))
        else:
            self.remaining_amount = self.payment_schedule_id.remaining_amount - self.booking_amount
