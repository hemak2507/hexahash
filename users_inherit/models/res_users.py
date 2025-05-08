from odoo import models, fields

class ResUser(models.Model):
    _inherit = "res.users"

    notification_type = fields.Selection(
        selection=[
            ('email', 'Handle by Emails'),
            ('inbox', 'Handle by NYDA')
        ],
        default='email'
    )