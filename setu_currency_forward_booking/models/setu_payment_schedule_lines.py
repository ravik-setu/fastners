from odoo import fields, models


class PaymentScheduleLines(models.Model):
    _name = 'setu.payment.schedule.lines'
    _description = "Setu Payment Schedule Lines"

    is_payment_received = fields.Boolean(string="Is Payment Received")
    payment_date = fields.Date(string="Payment Date")
    amount = fields.Float(string="Amount")
    currency_id = fields.Many2one(comodel_name="res.currency", string="Currency")
    company_id = fields.Many2one(comodel_name="res.company", string="Company")
    order_id = fields.Many2one(comodel_name="sale.order", string="Sale Order")
    picking_id = fields.Many2one(comodel_name="stock.picking", string="Delivery")
    forward_booking_id = fields.Many2one(comodel_name="setu.forward.booking", string="Booking")
    payment_schedule_id = fields.Many2one('setu.payment.schedule', string="Payment Schedule")

    def action_delete_schedule_line(self):
        """
                Author : Aastha Vora
                Date : 2nd July 2024
                Purpose : To delete payment schedule line from booking and remove booking record from payment schedule.
        """
        self.sudo().payment_schedule_id.remaining_amount += self.amount
        self.sudo().payment_schedule_id.forward_booking_ids = [(3, self.forward_booking_id.id)]
        self.sudo().unlink()
