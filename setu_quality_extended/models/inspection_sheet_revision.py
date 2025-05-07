from odoo import fields, models, api

class SetuQualityCheckSheetRevision(models.Model):
    _name = "setu.quality.check.sheet.revision"
    _inherit = ['mail.thread']
    _description = " Setu Quality Check Inspection Sheet Revision"

    inspection_sheet_id = fields.Many2one('setu.quality.check.sheet')

    name = fields.Char()

    date = fields.Date(default=fields.Date.today())
    company_id = fields.Many2one('res.company')
    team_id = fields.Many2one('setu.quality.alert.team')
    source = fields.Char()
    picking_id = fields.Many2one('stock.picking')
    production_id = fields.Many2one('mrp.production')
    product_id = fields.Many2one('product.product')
    lot_id = fields.Many2one('stock.lot')

    status = fields.Selection([('open', 'Open'),
                               ('accept', 'Accept'),
                               ('reject', 'Reject'),
                               ('acceptud', 'Accepted Under Deviation')], default='open')
    quantity_recieved = fields.Float()
    sampled_quantity = fields.Float()
    quantity_accepted = fields.Float()
    quantity_rejected = fields.Float()
    quantity_destructive = fields.Float()
    under_deviation = fields.Float()
    quality_check_ids = fields.One2many(
        'setu.quality.check.revision', 'inspection_sheet_id')