from odoo import fields, models, api


class PlanningLot(models.Model):
    _name = 'planning.lot'
    _description = 'Planning Lot'

    name = fields.Char()
    code = fields.Char()
    company_id = fields.Many2one(
        'res.company', 'Company', default=lambda self: self.env.company,
        index=True, required=True)
    planning_id = fields.Many2one("mrp.production.planning")

    def action_generate_serial(self, planning_id=False):
        code = self.env['ir.sequence'].next_by_code('planning.lot.seq')
        date_seq = "{}{}".format(str(fields.Datetime.today().month), str(fields.Datetime.today().date().year)[2:])
        return self.create({
            'code': code,
            'name': "{}/{}/{}".format(code, date_seq,
                                      planning_id.customer_id.code) if planning_id.customer_id.code else "{}/{}".format(
                code, date_seq),
        })
