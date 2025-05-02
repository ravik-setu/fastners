from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    def get_tax_amount(self, tax_group_name):
        taxes = self.env['account.tax']._prepare_tax_totals(
                    [x._convert_to_tax_base_line_dict() for x in self],
                    self.order_id.currency_id or self.order_id.company_id.currency_id,
                )
        for tax in taxes.get("groups_by_subtotal").get('Untaxed Amount'):
            if tax.get("tax_group_name") == tax_group_name:
                return round(tax.get("tax_group_amount"),2)
