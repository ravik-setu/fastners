from odoo import fields, models, api


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    planning_id = fields.Many2one('mrp.production.planning', related="production_id.planning_id")

    def button_start(self):
        res = super(MrpWorkorder, self).button_start()
        if not self.env.context.get('from_mo'):
            for rec in self:
                rec.production_id.button_start_stop()
        return res

    def button_pending(self):
        res = super().button_pending()
        if not self.env.context.get('from_mo'):
            for rec in self:
                rec.production_id.button_start_stop()
        return res