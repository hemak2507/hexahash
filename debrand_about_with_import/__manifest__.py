# -*- coding: utf-8 -*-
{
    'name': 'Debrand ERP V17 ',
    'license': 'LGPL-3',
    'summary': """This module allow you manage your customer support ticket, ticket portal, billings for support, Timesheets.""",
    'description': """
                    Website Helpdesk Support Ticket
                    """,
    'author': "ERPTechies",
    'website': "https://erptechies.com",
    'support': 'support@hashcodeit.com',
    "version": "17.0.1.0.0",
    'category': 'Services/Project',
    'depends': ['base', 'web','sale', 'website','base_setup','base_import','crm','stock','stock_sms',
               
                # 'website_portal',    
                ],
    'data': [
       # 'views/res_config_settings_views.xml', *****************
        #'views/crm_iap_lead_mining_request_views.xml',
        'views/crm_res_config_settings_views.xml',
        #'views/stock_iap_views.xml',
        'views/partner_form_inherit.xml',
        #'views/crm_iap_lead_mining_menu_inherit.xml',
        'views/crm_lead_views.xml',
        #'views/import_action_inherit.xml',
      
    ],
    'assets': {
        'web.assets_backend': [
            
           
            # 'debrand_about_with_import/static/src/views/res_config_edition.xml',
             #'debrand_about_with_import/static/src/**/*.xml',
            # 'debrand_about_with_import/static/src/views/generate_leads_views.xml',
            # 'debrand_about_with_import/static/src/core/**/*',
            # 'debrand_about_with_import/static/src/xml/*',
            # 'debrand_about_with_import/static/src/js/*',
           # 'debrand_about_with_import/static/src/import_action/import_action.js',
           #'debrand_about_with_import/static/src/import_action/import_action.xml',
           #'debrand_about_with_import/static/src/import_data_content/import_data_content.xml',
            
          
        ],
        'web.assets_frontend': [
            #'debrand_about_with_import/static/src/public/error_notifications.js',
           # 'debrand_about_with_import/static/src/core/**/*',
            
            ],
       
        },
    
    
    
    'images': [
        'static/description/img.png',
    ],
    'installable': True,
    'application': False,
    # 'auto_install' : True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
