{
    'name': 'Partner Custom Field',
    'version': '1.0',
    'author': 'Chenthur',
    'category': 'Customization',
    'summary': 'Adds a custom field to res.partner',
    'depends': ['base','base_vat','membership','contacts','sale','category_master','sub_category_master'],
    'data': [
        'views/res_partner.xml'
    ],
    'installable': True,
    'application': False,
}
