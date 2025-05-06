from odoo import fields, models, api


class StockBackorderConfirmation(models.TransientModel):
    _inherit = 'stock.backorder.confirmation'

    def process(self):
        for rec in self:
            for pickining in rec.backorder_confirmation_line_ids:
                for pick in pickining.picking_id.check_ids:
                    if pick.quality_state == 'none':
                        pick.quality_state = 'cancel'
            value = super().process()
            sheets = rec.pick_ids.filtered(lambda x: x.check_ids).inspection_sheet_ids.filtered(
                lambda x: x.state == 'open')
            if sheets:
                check_ids = sheets.mapped('quality_check_ids')
                if check_ids:
                    if len(check_ids) == 1:
                        self.env.cr.execute("""delete from setu_quality_check where id = {}""".format(check_ids[0].id))
                    else:
                        self.env.cr.execute("""delete from setu_quality_check where id in {}""".format(tuple(check_ids.ids)))

                if len(sheets) == 1:
                    self.env.cr.execute(
                        """update inspection_sheet set state = 'cancel' where id = {}""".format(sheets[0].id))
                else:
                    self.env.cr.execute(
                        """update inspection_sheet set state = 'cancel' where id in {}""".format(tuple(sheets.ids)))

        return value

    def process_cancel_backorder(self):
        res = super().process_cancel_backorder()
        for rec in self:
            sheets = rec.pick_ids.filtered(lambda x: x.check_ids).inspection_sheet_ids.filtered(
                lambda x: x.state == 'open')
            if sheets:
                check_ids = sheets.mapped('quality_check_ids')
                if check_ids:
                    if len(check_ids) == 1:
                        self.env.cr.execute("""delete from setu_quality_check where id = {}""".format(check_ids[0].id))
                    else:
                        self.env.cr.execute("""delete from setu_quality_check where id in {}""".format(tuple(check_ids.ids)))

                if len(sheets) == 1:
                    self.env.cr.execute(
                        """update inspection_sheet set state = 'cancel' where id = {}""".format(sheets[0].id))
                else:
                    self.env.cr.execute(
                        """update inspection_sheet set state = 'cancel' where id in {}""".format(tuple(sheets.ids)))

        return res

