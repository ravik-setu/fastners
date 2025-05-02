from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime


class PaymentScheduleBooking(models.TransientModel):
    _name = "setu.payment.schedule.booking.wizard"
    _description = "Setu Payment Schedule Booking Wizard"

    total_remaining_amount = fields.Float(string="Forward Booking Amount")
    remarks = fields.Text(string="Remarks")
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    hash_rate = fields.Monetary(string="Hash Rate", currency_field='currency_id')
    booking_type = fields.Selection(string="Booking Type",
                                    selection=[('existing', 'Add to Existing Booking'), ('new', 'Create New Booking')])
    forward_booking_id = fields.Many2one(comodel_name="setu.forward.booking", string="Forward Booking")
    currency_id = fields.Many2one(related="wizard_payment_schedule_line_ids.currency_id")
    bank_id = fields.Many2one(comodel_name="res.bank", string="Bank")
    wizard_payment_schedule_line_ids = fields.One2many(comodel_name='setu.payment.schedule.booking.line.wizard',
                                                       inverse_name='booking_wizard_id',
                                                       string="Payment Schedule Lines")

    @api.onchange('forward_booking_id')
    def onchange_forward_booking(self):
        if self.forward_booking_id:
            remaining_amount = self.forward_booking_id.booking_amount - sum(
                self.forward_booking_id.payment_schedule_line_ids.mapped('amount'))
            self.total_remaining_amount = remaining_amount if remaining_amount > 0 else 0

    @api.onchange('total_remaining_amount')
    def _onchange_total_remaining_amt(self):
        """
            Author : Aastha Vora
            Date : 3rd July 2024
            Purpose : This method is used to get total remaining amount for the selected payment schedules.
        """
        lst = []
        payment_schedule_ids = self.env.context.get('active_ids')
        if payment_schedule_ids:
            if self.wizard_payment_schedule_line_ids:
                self.wizard_payment_schedule_line_ids = [(5,)]

            payment_schedules = self.env['setu.payment.schedule'].search([('id', 'in', payment_schedule_ids),
                                                                          ('remaining_amount', '>', 0),
                                                                          '|',
                                                                          ('forward_booking_ids', '=', False),
                                                                          ('forward_booking_ids', '!=', False)])
            if payment_schedules:
                if len(payment_schedules.mapped('currency_id')) > 1 or len(payment_schedules.mapped('company_id')) > 1:
                    raise UserError(_("You can create Booking for payments with similar company and similar currency."))
                remaining_amount = self.total_remaining_amount
                amount = self.total_remaining_amount
                payment_dates = sorted(payment_schedules.mapped('payment_date'))
                self.start_date = payment_dates[0]
                self.end_date = payment_dates[-1]
                for rec in payment_schedules:
                    schedule_amount = rec.remaining_amount or rec.amount
                    line_booking_amount = schedule_amount
                    if remaining_amount > 0:
                        remaining_amount -= schedule_amount
                        line_remaining_amount = abs(amount - schedule_amount) if remaining_amount < 0 else 0
                        line_booking_amount -= line_remaining_amount
                        amount -= schedule_amount
                    else:
                        line_remaining_amount = schedule_amount
                        line_booking_amount = 0
                    if self.booking_type == 'existing' and self.forward_booking_id.booking_amount <= sum(
                            self.forward_booking_id.payment_schedule_line_ids.mapped('amount')):
                        line_booking_amount = 0
                    vals = {'payment_schedule_id': rec.id,
                            'remaining_amount': line_remaining_amount,
                            'booking_amount': line_booking_amount,
                            'currency_id': rec.currency_id.id,
                            'payment_date': rec.payment_date,
                            'company_id': rec.company_id.id,
                            'order_id': rec.order_id.id,
                            'booking_wizard_id': self._origin.id}
                    lst.append((0, 0, vals))
                self.write({'wizard_payment_schedule_line_ids': lst})

    def action_save_booking(self):
        """
            Author : Aastha Vora
            Date : 3rd July 2024
            Purpose : This method is used to add payment schedule to existing booking or to create new booking.
        """
        if self.end_date < self.start_date:
            raise ValidationError(_("You can not set End Date prior than Start Date."))
        payment_schedule_lines = self.wizard_payment_schedule_line_ids.filtered(lambda x: x.booking_amount > 0)
        booking_id = False
        if not payment_schedule_lines:
            raise ValidationError(_("You Can not Add Payment Schedule Lines with 0 Booking Amount to Forward Booking."))
        if self.booking_type == 'existing':
            for line in payment_schedule_lines:
                existing_schedule_line = self.forward_booking_id.payment_schedule_line_ids.filtered(
                    lambda x: x.order_id == line.order_id and x.payment_date == line.payment_date)
                if existing_schedule_line:
                    existing_schedule_line.amount += line.booking_amount
                else:
                    vals = {'payment_date': line.payment_date,
                            'amount': line.booking_amount,
                            'currency_id': line.currency_id.id,
                            'company_id': line.company_id.id,
                            'forward_booking_id': self.forward_booking_id.id,
                            'order_id': line.order_id.id,
                            'payment_schedule_id': line.payment_schedule_id.id}
                    self.forward_booking_id.write({'payment_schedule_line_ids': [(0, 0, vals)]})
                line.payment_schedule_id.write({'remaining_amount': line.remaining_amount,
                                                'forward_booking_ids': [(4, self.forward_booking_id.id)]})
            booking_id = self.forward_booking_id

        if self.booking_type == 'new':
            if not self.hash_rate:
                raise ValidationError("Hash Rate Should be Greater Than 0.")
            vals = []
            booking_id = self.env['setu.forward.booking']
            payment_schedule_id = payment_schedule_lines.payment_schedule_id

            if payment_schedule_id:
                vals.append({'start_date': self.start_date,
                             'end_date': self.end_date,
                             'company_id': payment_schedule_id.company_id.id,
                             'currency_id': payment_schedule_id.currency_id.id,
                             'booking_amount': self.total_remaining_amount,
                             'payment_schedule_ids': [(4, rec.id) for rec in payment_schedule_id],
                             'order_ids': [(4, order.id) for order in payment_schedule_id.order_id],
                             'deal_date': datetime.now(),
                             'bank_id': self.bank_id.id,
                             'hash_rate': self.hash_rate,
                             'remarks': self.remarks
                             })
                new_booking = booking_id.create(vals)
                for rec in payment_schedule_lines:
                    lst = {'order_id': rec.order_id.id,
                           'payment_date': rec.payment_date,
                           'amount': rec.booking_amount,
                           'currency_id': rec.currency_id.id,
                           'company_id': rec.company_id.id,
                           'payment_schedule_id': rec.payment_schedule_id.id}
                    new_booking.write({'payment_schedule_line_ids': [(0, 0, lst)]})
                    rec.payment_schedule_id.write({'forward_booking_ids': [(4, new_booking.id)],
                                                   'remaining_amount': rec.remaining_amount})
                new_booking.action_confirm()
                booking_id = new_booking
        if booking_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Forward Booking',
                'res_model': 'setu.forward.booking',
                'target': 'current',
                'views': [
                    (self.env.ref('setu_currency_forward_booking.setu_currency_forward_booking_form_view').id, 'form')],
                'res_id': booking_id.id
            }
