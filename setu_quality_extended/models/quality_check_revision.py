from odoo import fields, models, api


class QualityCheckRevision(models.Model):
    _name = "setu.quality.check.revision"
    _description = "Quality Check Revision"

    inspection_sheet_id = fields.Many2one('setu.quality.check.sheet.revision')

    point_id = fields.Many2one('setu.quality.point', 'Control Point')
    title = fields.Char(related="point_id.title")
    test_type = fields.Char("TTP")
    quality_state = fields.Selection([
        ('none', 'To do'),
        ('pass', 'Passed'),
        ('fail', 'Failed'),
        ('cancel', 'Cancel')], string='Status', tracking=True,
        default='none', copy=False, store=True, compute='_set_state')
    test_type_id = fields.Many2one('setu.quality.point.test_type')
    test_method_id = fields.Many2one(
        'setu.quality.test.method', related="point_id.test_method_id")
    measure = fields.Float()
    norm = fields.Float(related="point_id.norm")
    norm_unit = fields.Char(related="point_id.norm_unit")
    tolerance_min = fields.Float(related="point_id.tolerance_min")
    tolerance_max = fields.Float(related="point_id.tolerance_max")

    @api.depends('test_type', 'measure')
    def _set_state(self):
        for rec in self:
            if rec.test_type == 'measure':
                if rec.measure >= rec.tolerance_min and rec.measure <= rec.tolerance_max:
                    rec.quality_state = 'pass'
                else:
                    rec.quality_state = 'fail'
            else:
                rec.quality_state = 'none'
