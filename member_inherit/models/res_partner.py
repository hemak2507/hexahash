from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    #name = fields.Char(string="Name", required=False)
    person_type = fields.Selection(
        selection=[
            ('person','Individual'),
            ('company','Company'),
            ('ngo','NGO'),
            ('others','Others')
        ],
        default='person'
    )
    contact_person = fields.Char(string="Contact Person")
    free_member = fields.Boolean(string="Free Member")
    sur_name = fields.Char(string="Surname")
    name_custom = fields.Selection(
        selection = [
            ('mr', 'Mr'),
            ('ms', 'Ms'),
            ('mrs', 'Mrs'),
            ('dr', 'Dr.'),
            ('prof', 'Prof.')
        ],
        
        default='mr'
    )
    corridor = fields.Selection(
        selection=[
            ('Central Corridor','Central Corridor'),
            ('East Corridor','East Corridor'),
            ('North Corridor','North Corridor'),
            ('South Corridor','South Corridor'),
            ('West Corridor','West Corridor'),
        ]
    )
    id_number = fields.Char(string="ID Number")
    co_reg = fields.Char(string="Co Reg")
    ngo_number = fields.Char(string="NGO Number")
    cat_id = fields.Many2one('category.master',string="Category")
    sub_cat_id = fields.Many2one('sub.category.master',string="Sub Category")
    