from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_quotation_send(self):
        """Extend the original behavior of action_quotation_send with custom view and name"""
        
        # Call the parent method using super()
        res = super(SaleOrder, self).action_quotation_send()

        # Modify or add custom context data
        ctx = res.get('context', {})  # Get context from the result of super()
        
        # Update the view mode and set a custom name
        res.update({
            'view_mode': 'form',  # Change view_mode to 'tree'
            'name': _('Compose Email'),  # Set the custom name of the action
            'context': ctx,
        })
        
        return res
