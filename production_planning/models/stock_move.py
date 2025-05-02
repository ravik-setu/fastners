from odoo import fields, models, api
import logging
_logger = logging.getLogger(__name__)

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _is_internal(self):
        """Check if the move should be considered as a dropshipping move so that the cost method
        will be able to apply the correct logic.

        :returns: True if the move is a dropshipping one else False
        :rtype: bool
        """
        self.ensure_one()
        return self.picking_type_id.code == 'internal' if self.env.context.get('is_custom_valuation') and self.location_dest_id.is_wip_stock_location or self.location_id.is_wip_stock_location else False

    def _action_done(self, cancel_backorder=False):
        res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
        for rec in self.filtered(
                lambda move: move.product_id.type == 'product' and move.product_id.categ_id.property_valuation == 'real_time'):
            if rec._is_internal() and (rec.location_id.is_wip_stock_location or rec.location_dest_id.is_wip_stock_location):
                _logger.info("Start Creating journal entry for move: {}".format(rec.id))
                am_vals = rec._prepare_account_move_vals_for_internal()
                try:
                    account_moves = self.env['account.move'].sudo().create(am_vals)
                    account_moves._post()
                except Exception as e:
                    self.message_post(body=e)
                    continue
                _logger.info("Journal entries {} created successfully for move: {}".format(account_moves._ids, rec.id))
        return res

    def _prepare_account_move_vals_for_internal(self):
        journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
        valuation_partner_id = self._get_partner_id_for_valuation_lines()
        description = '{} - {}'.format(self.picking_id.name,
                                       self.product_id.name) if self.picking_id else self.product_id.name
        for move in self:
            acc_dest = self.location_dest_id.valuation_in_account_id.id or acc_dest
            unit_cost = self._get_price_unit()
            quantity = 0
            for valued_move_line in move.move_line_ids:
                quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.quantity,
                                                                         move.product_id.uom_id)
            value = move.company_id.currency_id.round(unit_cost * quantity)
            move_ids = self._prepare_account_move_line(quantity, value, acc_dest, acc_src, False,
                                                       description)
        return {
            'journal_id': journal_id,
            'line_ids': move_ids,
            'partner_id': valuation_partner_id,
            'date': fields.Date.context_today(self),
            'ref': description,
            'stock_move_id': self.id,
            'move_type': 'entry',
            'is_storno': self.env.context.get('is_returned') and self.env.company.account_storno,
        }

    def _get_accounting_data_for_valuation(self):
        """ Return the accounts and journal to use to post Journal Entries for
        the real-time valuation of the quant. """
        self.ensure_one()
        journal_id, acc_src, acc_dest, acc_valuation = super(StockMove, self)._get_accounting_data_for_valuation()
        if self._is_out() and self.location_id.is_wip_stock_location:
            if self._is_returned(valued_type='out'):
                acc_src = self.location_id.valuation_in_account_id.id or acc_src
            else:
                acc_dest = self.location_id.valuation_in_account_id.id or acc_dest
        return journal_id, acc_src, acc_dest, acc_valuation
