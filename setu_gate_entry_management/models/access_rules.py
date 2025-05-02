from odoo import models, api, tools

class MenuAccessControl(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    @tools.ormcache_context('self._uid', 'debug', keys=('lang',))
    def load_menus(self, debug):
        res = super().load_menus(debug)
        if self.env.user.has_group('setu_gate_entry_management.group_setu_gate_entry_user') and self.env.user.has_group('setu_gate_entry_management.group_setu_gate_entry_manager'):
            return res
        elif self.env.user.has_group('setu_gate_entry_management.group_setu_gate_entry_user'):
            gate_pass_menu_id = self.env.ref('setu_gate_entry_management.gate_pass_main_menu')
            dic = {gate_pass_menu_id.id:res.get(gate_pass_menu_id.id)}
            for child in res.get(gate_pass_menu_id.id).get('children'):
                dic.update({child:res.get(child)})
            dic.update({'root': {
                'id': False,
                'name': 'root',
                'parent_id': [-1, ''],
                'children': [gate_pass_menu_id.id],
            }})
            return dic
        else:
            return res
