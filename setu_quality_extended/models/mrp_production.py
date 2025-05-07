from odoo import fields, models, api,_
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    date_confirm = fields.Datetime()
    set_interval = fields.Boolean()
    inspection_sheet_ids = fields.One2many('setu.quality.check.sheet', 'production_id')
    valid_inspection_sheet_count = fields.Integer(compute="_compute_valid_inspection_sheet")
    check_ids = fields.One2many('setu.quality.check', 'production_id', string="Checks")

    @api.depends('inspection_sheet_ids.state')
    def _compute_valid_inspection_sheet(self):
        for production in self:
            production.valid_inspection_sheet_count = len(
                production.inspection_sheet_ids.filtered(lambda x: x.state != 'cancel'))

    @api.onchange('qty_producing')
    def _onchange_qty_producing(self):
        for production in self:
            if any(production.inspection_sheet_ids.filtered(lambda x: x.state in ('accept', 'released'))):
                raise ValidationError("You can only update the quantity inspection sheet when it is in an open state.")
            open_inspection_sheet_ids = production.inspection_sheet_ids.filtered(lambda x: x.state == 'open')
            if open_inspection_sheet_ids:
                open_inspection_sheet_ids.write({'quantity_recieved': production.qty_producing})

    def action_confirm(self):
        res = super().action_confirm()
        self.date_confirm = datetime.now()
        return res

    def button_mark_done(self):
        res = super(MrpProduction, self).button_mark_done()
        if not self.inspection_sheet_ids.filtered(lambda x: x.state != 'cancel') and self.check_ids:
            raise UserError(_("Please Generate Inspection Sheet."))

        if self.inspection_sheet_ids.filtered(lambda x: x.state == 'open') and self.check_ids:
            raise UserError(_("Please Complete the QC Check in the Inspection Sheet1."))

        if self.inspection_sheet_ids.filtered(lambda x: x.state == 'accept') and self.check_ids:
            raise UserError(_("Please Release the Inventory From QC to Move the Product to Stock."))
        return res

    def button_genarate_inpection_sheet(self):
        for production in self:
            if production.check_ids:
                if not production.check_ids.filtered(lambda x: x.inspection_sheet_id.state != 'cancel').mapped(
                        'inspection_sheet_id'):
                    rec = production.check_ids[0]
                    vals = {'product_id': rec.product_id.id,
                            'team_id': rec.team_id.id,
                            'company_id': rec.company_id.id,
                            'lot_id': rec.lot_id.id,
                            'quantity_recieved': rec.production_id.qty_producing,
                            'production_id': rec.production_id.id,
                            }
                    if rec.production_id.qty_producing <= 0:
                        raise UserError(_("Quantity Producing Should Be Greter Then Zero"))

                    sheet = self.env['setu.quality.check.sheet'].create(vals).id
                    production.check_ids.write({'inspection_sheet_id': sheet})

    def view_quality_inspection_sheet_action(self):
        return {
            'name': 'Inspection Sheets',
            'view_mode': 'tree,form',
            'res_model': 'setu.quality.check.sheet',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('production_id', '=', self.id)],
        }
