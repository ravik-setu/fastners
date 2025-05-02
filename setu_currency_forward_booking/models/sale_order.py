# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta, datetime


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    delivery_delay = fields.Integer(string="Delivery Delay", tracking=True, copy=False)
    order_booking_rate = fields.Float(string="Order Booking Rate", tracking=True, copy=False)
    payment_schedule_ids = fields.One2many(comodel_name='setu.payment.schedule', inverse_name='order_id',
                                           string="Payment Schedule")
    payment_schedule_line_ids = fields.One2many(comodel_name='setu.payment.schedule.lines', inverse_name='order_id',
                                           string="Payment Schedule Lines")


    def action_confirm(self):
        res = super(SaleOrder,self).action_confirm()
        if self.state == 'sale':
            date = self.commitment_date
            if self.commitment_date:
                date = self.commitment_date
            elif not self.commitment_date and self.picking_ids:
                picking = self.sudo().picking_ids.filtered(lambda x: x.state != 'cancel')
                if picking:
                    date = picking[0].scheduled_date
        if (self.commitment_date or self.payment_term_id or self.delivery_delay or self.order_line) and date:
            if self.payment_term_id:
                vals = self.get_payment_schedule_vals(self, date)
                vals and self.env['setu.payment.schedule'].create(vals)
        return res
        
        
    def write(self, values):
        res = super().write(values)
        for order in self:
            if order.state != 'draft':
                date = order.commitment_date
                if values.get('commitment_date'):
                    date = datetime.strptime(values.get('commitment_date'), '%Y-%m-%d %H:%M:%S')
                elif not order.commitment_date and order.picking_ids:
                    picking = order.sudo().picking_ids.filtered(lambda x: x.state != 'cancel')
                    if picking:
                        date = picking[0].scheduled_date
                if (values.get('commitment_date') or values.get('payment_term_id') or values.get('delivery_delay') or values.get('order_line')) and date:
                    if order.payment_term_id:
                        if order.payment_schedule_ids.mapped('forward_booking_ids'):
                            raise ValidationError(_("For Some of Payment Schedules Booking is Already created."))
                        vals = order.get_payment_schedule_vals(order,date)
                        vals and self.env['setu.payment.schedule'].create(vals)
        return res

    def get_payment_schedule_vals(self,order,date):
        vals = []
        order.sudo().payment_schedule_ids.unlink()
        if order.delivery_delay:
            date = date + timedelta(days=order.delivery_delay)
        data = order.payment_term_id._compute_terms(date_ref=date,
                                                    currency=order.currency_id,
                                                    company=order.company_id,
                                                    tax_amount=order.amount_tax,
                                                    tax_amount_currency=order.amount_tax,
                                                    sign=1,
                                                    untaxed_amount=order.amount_untaxed,
                                                    untaxed_amount_currency=order.amount_untaxed)

        for rec in data.get('line_ids', {}):
            vals.append({'payment_date': rec['date'],
                         'order_id': order.id,
                         'amount': rec['company_amount'],
                         'currency_id': order.currency_id.id,
                         'company_id': order.company_id.id,
                         'remaining_amount': rec['company_amount']})
        return vals

    def _prepare_invoice(self):
        res = super()._prepare_invoice()
        order_booking_rate = self.order_booking_rate
        if order_booking_rate:
            res.update({'order_booking_rate': order_booking_rate})
        return res
