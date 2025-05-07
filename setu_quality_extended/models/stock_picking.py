from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    inspection_sheet_ids = fields.One2many('setu.quality.check.sheet', 'picking_id')
    date_confirm = fields.Datetime()
    set_interval = fields.Boolean()
    qc_duplication_inp_sheet = fields.Boolean()
    quality_sheet_status = fields.Selection(
        [('not_completed', 'Not Completed'), ('partial', 'Partial Completed'), ('accepted', 'Accepeted'),
         ('fully_completed', 'Fully Completed'), ('cancelled', 'Cancelled')], compute="get_quality_status",
        string="QC Status", store=True)

    @api.depends('inspection_sheet_ids.state')
    def get_quality_status(self):
        for picking in self:
            picking.quality_sheet_status = False
            if picking.inspection_sheet_ids:
                if all([True if sheet.state == 'open' else False for sheet in
                        picking.inspection_sheet_ids.filtered(lambda x: x.state != 'cancel')]):
                    picking.quality_sheet_status = 'not_completed'
                elif all([True if sheet.state == 'accept' else False for sheet in picking.inspection_sheet_ids]):
                    picking.quality_sheet_status = 'accepted'
                elif all([True if sheet.state == 'released' else False for sheet in picking.inspection_sheet_ids]):
                    picking.quality_sheet_status = 'fully_completed'
                elif all([True if sheet.state == 'cancel' else False for sheet in picking.inspection_sheet_ids]):
                    picking.quality_sheet_status = 'cancelled'
                else:
                    picking.quality_sheet_status = 'partial'

    def action_cancel(self):
        res = super(StockPicking, self).action_cancel()
        for picking in self:
            if picking.inspection_sheet_ids:
                picking.inspection_sheet_ids.button_cancel()
        return res

    def view_inspection_sheet(self):
        return {
            'name': 'Inspection Sheets',
            'view_mode': 'tree,form',
            'res_model': 'setu.quality.check.sheet',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('picking_id', '=', self.id)],
        }

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        for picking in self:
            if picking.check_ids:
                picking_sheets_ids = picking.inspection_sheet_ids
                if picking_sheets_ids:
                    if all([True if sheet.state == 'open' else False for sheet in picking_sheets_ids]):
                        raise UserError(_("Please Complete the QC Check in the Inspection Sheet."))

                elif not sum(picking.move_ids_without_package.mapped('quantity_done')):
                    raise UserError(_("Please Complete the QC Check in the Inspection Sheet."))

                sheets = picking.inspection_sheet_ids.filtered(lambda x: x.state == 'accept')

                for sheet in sheets:
                    if not sheet.processed:
                        raise UserError(_("Please Release the Inventory From QC to Move the Product to Stock."))

            if picking.picking_type_id.create_backorder == 'always':
                sheets = picking.inspection_sheet_ids.filtered(lambda x: x.state == 'open')
                if sheets:
                    check_ids = sheets.mapped('quality_check_ids')
                    if check_ids:
                        if len(check_ids) == 1:
                            self.env.cr.execute("""delete from setu_quality_check where id = {}""".format(check_ids[0].id))
                        else:
                            self.env.cr.execute(
                                """delete from setu_quality_check where id in {}""".format(tuple(check_ids.ids)))
                    if len(sheets) == 1:
                        self.env.cr.execute(
                            """update inspection_sheet set state = 'cancel' where id = {}""".format(sheets[0].id))
                    else:
                        self.env.cr.execute(
                            """update inspection_sheet set state = 'cancel' where id in {}""".format(tuple(sheets.ids)))

        return res