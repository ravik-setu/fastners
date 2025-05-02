from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    forward_booking_ids = fields.One2many(comodel_name='setu.forward.booking.wizard',
                                          inverse_name='register_payment_id',
                                          string="Forward Booking")

    def _create_payments(self):
        """
        Author : Aastha Vora
        Date : 3rd July 2024
        Purpose : This method is used to create payment and add that payment record to selected bookings.
        """
        for rec in self.forward_booking_ids:
            if rec.booking_amount > rec.remaining_amount:
                raise ValidationError(_("You Can not Enter Amount More Than the Remaining Amount."))
        res = super(AccountPaymentRegister, self)._create_payments()
        vals = []
        active_id = self.env.context.get('active_id')
        invoice_id = self.env['account.move'].browse(active_id)
        order_id = invoice_id.invoice_line_ids.sale_line_ids.order_id
        if self.forward_booking_ids:
            if sum(self.forward_booking_ids.mapped('booking_amount')) > self.amount:
                raise ValidationError(_("Booking Amount Should not Greater than the Payment Amount."))
            for rec in self.forward_booking_ids.filtered(lambda x: x.booking_amount > 0):
                vals.append({'order_id': order_id.id,
                             'payment_id': res.id,
                             'payment_received_date': self.payment_date,
                             'received_amount': rec.booking_amount,
                             'currency_id': self.currency_id.id,
                             'order_booking_rate': invoice_id.order_booking_rate,
                             'forward_booking_id': rec.forward_booking_id.id})
            self.env['setu.bank.received.amount.details'].create(vals)

        return res

    @api.model
    def default_get(self, fields_list):
        """
        Author : Aastha Vora
        Date : 3rd July 2024
        Purpose : To add default booking records in register payment wizard.
        """
        res = super(AccountPaymentRegister, self).default_get(fields_list)
        vals = []
        move_id = self.env.context["active_id"]
        order_id = self.env['account.move'].browse(move_id).invoice_line_ids.sale_line_ids.order_id
        booking_ids = self.env['setu.payment.schedule.lines'].search(
            [('order_id', '=', order_id.id)]).forward_booking_id
        for rec in booking_ids:
            booking_amt = sum(rec.payment_schedule_line_ids.filtered(lambda x: x.order_id == order_id).mapped('amount'))
            recieved_amt = sum(
                rec.bank_received_amount_ids.filtered(lambda x: x.order_id == order_id).mapped('received_amount'))
            vals.append((0, 0, {'forward_booking_id': rec.id,
                                'booking_amount': booking_amt - recieved_amt}))
        res.update({'forward_booking_ids': vals})

        return res
