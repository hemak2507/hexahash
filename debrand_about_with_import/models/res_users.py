from odoo import models, fields,api ,_

class ResUsers(models.Model):
    _inherit = 'res.users'

    odoobot_state = fields.Char( string="Bot State", group_operator=False, filterable=False)
    odoobot_failed = fields.Boolean(string="Bot Failed",group_operator=False, filterable=False)
    #
    # @api.model
    # def fields_get(self, fields=None):
    #     fields_to_hide = ['odoobot_state', 'odoobot_failed']
    #     res = super(ResUsers, self).fields_get(fields)
    #     for field in fields_to_hide:
    #         if field in res:
    #             res[field]['searchable'] = False
    #     return res
    
    
    def get_fields_to_ignore_in_search(self): 
        return ['odoobot_state', 'odoobot_failed']

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(ResUsers, self).fields_get(allfields, attributes=attributes)
        for field in self.get_fields_to_ignore_in_search():
            if res.get(field):
                res[field]['searchable'] = False  # Hides the field from search
                res[field]['sortable'] = False #// To Hide Field From Group by        
                res[field]['exportable'] = False #// To Hide Field From Export List
        return res