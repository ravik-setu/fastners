from odoo import fields, models, api


class QualityAlertTeam(models.Model):
    _inherit = 'setu.quality.alert.team'

    approver_id = fields.Many2one('res.users')
    approver_ids = fields.Many2many('res.users', string='Approver')
    quality_inspector = fields.Many2many(
        'hr.employee', string="Quality Inspector")
    inspection_sheet_count = fields.Integer(
        '# Inspection Sheet Alerts', compute='_compute_inspection_sheet_count')
    reject_destructive_operation_type = fields.Many2one('stock.picking.type')

    def _compute_inspection_sheet_count(self):
        sheet_data = self.env['setu.quality.check.sheet'].read_group(
            [('team_id', 'in', self.ids), ('state', 'in',('open','accept')), ('processed', '=',False)], ['team_id'], ['team_id'])
        sheet_result = dict(
            (data['team_id'][0], data['team_id_count']) for data in sheet_data)
        for team in self:
            team.inspection_sheet_count = sheet_result.get(team.id, 0)