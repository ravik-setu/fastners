from odoo import fields, models, api
import num2words


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def get_tax_in_words(self):
        tax_list = self.tax_totals.get('groups_by_subtotal').get('Untaxed Amount')
        data = {}
        for tax in tax_list:
            if tax.get('tax_group_name') in ['SGST', 'CGST']:
                data.update({tax.get('tax_group_name'): tax.get('tax_group_amount', '')})
        return self.currency_id.amount_to_text(data.get('CGST') + data.get('SGST'))
