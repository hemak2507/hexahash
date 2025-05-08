from odoo import models, fields, api, Command,_ 
#from odoo.exceptions import UserError
from odoo.exceptions import UserError,ValidationError

from datetime import timedelta
import base64
from PIL import Image
from io import BytesIO
import pytz


class Event(models.Model):
    _inherit = 'event.event'

    date_begin = fields.Datetime('Begin Date')
    date_end = fields.Datetime('End Date')
    
    date_tz = fields.Selection(
        [(tz, tz) for tz in sorted(pytz.all_timezones)],
        string="Timezone",
        default="Africa/Johannesburg"
    )

    # Define the computed field for the duration in days
    days_count = fields.Integer('Days', compute='_compute_duration_days', store=True)
    # partner_ids = fields.Many2many(
    #     'res.partner', string="Event Invites",
    #     help="Select users to invite to the event.",
    #     domain=[("membership_state", "in", ["invoiced", "paid", "free"])]
    # )
    invite_partner_ids = fields.One2many(
        'event.partner.line', 'event_id', string="Event Invitees",
        help="Manage event invitees and their invitation status."
    )
    
    reminder_days_before_event = fields.Integer(
        string="EventList Mail Reminder",
        default=1,  # Default to 1 day before the event
        help="Number of days before the event to send reminder emails to attendees."
    )
    invite_track_ids = fields.One2many(
        'event.invite.track', 'event_id', string='Invites'
    )
    invite_count = fields.Integer(
        string='Invite Count', compute='_compute_invite_count'
    )

    def _compute_invite_count(self):
        for event in self:
            event.invite_count = len(event.invite_track_ids)

    def action_set_booked(self):
        #booked_stage = self.env.ref('event_inherit.stage_booked')
        self.write({'stage_id': 2})

    def action_set_announced(self):
        #announced_stage = self.env.ref('event_inherit.stage_announced')
        self.write({'stage_id': 3})

    def action_set_ended(self):
        #ended_stage = self.env.ref('event_inherit.stage_ended')
        self.write({'stage_id': 4})

    def action_set_cancelled(self):
        #cancelled_stage = self.env.ref('event_inherit.stage_cancelled')
        self.write({'stage_id': 5})

    @api.depends('date_begin', 'date_end')
    def _compute_duration_days(self):
        for record in self:
            if record.date_begin and record.date_end: 
                # Convert Datetime fields to Python datetime objects
                begin = record.date_begin
                end = record.date_end
            
                # Calculate the difference in days
                duration = (end - begin).days
                record.days_count = duration
            else:
                # Set days_count to 0 if either date is missing
                record.days_count = 0



    corridor = fields.Selection(
        selection=[
            ('Central Corridor','Central Corridor'),
            ('East Corridor','East Corridor'),
            ('North Corridor','North Corridor'),
            ('South Corridor','South Corridor'),
            ('West Corridor','West Corridor'),
        ]
    )
    list_ids = fields.One2many(
        'event.list', 'event_id', string='Event List', copy=True,
        compute='_compute_event_ticket_ids', readonly=False, store=True)
    image = fields.Image(string="Email Background Image", help="This image will be used as the background in email templates.")


    # category_id = fields.Many2one('category.master',string="Category")
    # sub_category_id = fields.Many2one('sub.category.master',string="Sub Category")
    
    @api.constrains('list_ids')
    def _check_list_ids(self):
        for event in self:
            if not event.list_ids:
                raise ValidationError("You must add at least one order line in the Event List before saving.")

    @api.depends('list_ids')
    def _compute_event_ticket_ids(self):
        """ Update event configuration from its event type. Depends are set only
        on event_type_id itself, not its sub fields. Purpose is to emulate an
        onchange: if event type is changed, update event configuration. Changing
        event type content itself should not trigger this method.

        When synchronizing tickets:

          * lines that have no registrations linked are remove;
          * type lines are added;

        Note that updating event_ticket_ids triggers _compute_start_sale_date
        (start_sale_datetime computation) so ensure result to avoid cache miss.
        """
        for event in self:
            if not event.event_type_id and not event.event_ticket_ids:
                event.event_ticket_ids = False
                continue

            # lines to keep: those with existing registrations
            tickets_to_remove = event.event_ticket_ids.filtered(lambda ticket: not ticket._origin.registration_ids)
            command = [Command.unlink(ticket.id) for ticket in tickets_to_remove]
            if event.event_type_id.event_type_ticket_ids:
                command += [
                    Command.create({
                        attribute_name: line[attribute_name] if not isinstance(line[attribute_name], models.BaseModel) else line[attribute_name].id
                        for attribute_name in self.env['event.type.ticket']._get_event_ticket_fields_whitelist()
                    }) for line in event.event_type_id.event_type_ticket_ids
                ]
            event.event_ticket_ids = command
            
    def action_event_invite_track1(self):
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Event Invite Track',
            'view_mode': 'tree',
            'res_model': 'event.invite.track',
            'domain': [('event_id', '=', self.id)],
        }  
            
    
            
    def action_send_invites(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')  # Get the base URL
        # for event in self:
        #     if not event.partner_ids:
        #         raise UserError(_("Please select at least one invite."))
        #
        #     for partner in event.partner_ids:
        #         if not partner.email:
        #             raise UserError(_(f"The invite {partner.name} does not have an email address."))
        for event in self:
            if not event.invite_partner_ids:
                raise UserError(_("Please select at least one invite."))

            for partner in event.invite_partner_ids:
                
                if partner.invited:
                    continue  # Skip sending email if already invited
                if not partner.partner_id.email:
                    raise UserError(
                        _("The invitee '%s' does not have an email address.")
                        % partner.partner_id.name
                    )
    
                subject = f"You're Invited: {event.name}"
                static_image_url = f"{base_url}/event_inherit/static/src/img/white.png"  # URL for the static white image
                dynamic_image_url = f"{base_url}/web/image/event.event/{event.id}/image"
                if event.image:
                    background_image = dynamic_image_url  # Use the dynamic image URL if an event image exists
                else:
                    background_image = static_image_url  # Use the static image URL if no event image exists

                # event_start = event.date_begin.strftime('%d-%m-%Y %H:%M') if event.date_begin else "Not Set"
                # event_end = event.date_end.strftime('%d-%m-%Y %H:%M') if event.date_end else "Not Set"
                event_start = ((event.date_begin + timedelta(hours=5, minutes=30)).strftime('%d-%m-%Y %H:%M')if event.date_begin else "Not Set")
                event_end = ((event.date_end + timedelta(hours=5, minutes=30)).strftime('%d-%m-%Y %H:%M')if event.date_end else "Not Set")
               
                #background-image: url('{background_image}'); 
                body_message = f"""
                <div style=" 
                background-color: transparent; 
            


            background-size: cover; 
            background-repeat: no-repeat; 
            background-position: center; 
            padding: 20px; 
            border-radius: 10px;">
                <p>Dear {partner.partner_id.name},</p>
                <p>We are delighted to invite you to our event <strong style="color:#215577;">{event.name}</strong>.</p>
                <p>Event Start from <strong style="color:#215577;">{event_start}</strong> To <strong style="color:#215577;">{event_end}</strong>.</p>
                <table   style="border-collapse: collapse; width: 40%;">
                                    <tr >                                         <td style="width: 6%;vertical-align:top;"><span><img src="/web_editor/font_to_img/61505/rgb(33,63,119)/34" style="padding:2px;max-width:inherit;" height="24" alt=""/></span>
                                     <b style="color:#215577;">Venue : </b> </td>
                                                                
                                                                <td style="padding: 0px 10px 0px 10px;width:34%;vertical-align:top;">
                                                                    <t t-if="event_address">
                                                                        <t t-set="location" t-value="''"/>
                                    <br/>
                                                                        
                                    <div style="padding-right: 10px; " t-out="object.event_id.address_id.name">{event.address_id.name  or ''}</div>
                                                                        
                                    
                                        <div t-out="object.event_id.address_id.street">{event.address_id.street  or ''}</div>
                                        
                                    
                                        <div t-out="object.event_id.address_id.street2">{event.address_id.street2  or ''}</div>
                                        
                                    
                                    <div>
                                    
                                        <t t-out="object.event_id.address_id.city">{event.address_id.city  or '' }</t>,
                                    
                                    
                                        <t t-out="object.event_id.address_id.state_id.name">{event.address_id.state_id.name or ''}</t>,
                                    
                                        <t t-out="object.event_id.address_id.zip">{event.address_id.zip  or ''}</t>
                                   
                                    </div>
                                    
                                        <div t-out="object.event_id.address_id.country_id.name">{event.address_id.country_id.name  or ''}</div>
                                   
                                </t>
                            </td>


                    </tr> </table><br/>
                <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">
                    <tr style="background-color: #f2f2f2;">
                        <th style="text-align: left;color: white; background-color: #215577;width:20%;">Event List</th>
                        <th style="text-align: left;color: white; background-color: #215577; width:20%;">Event Start</th>
                        <th style="text-align: left;color: white; background-color: #215577; width:20%;">Event End</th>
                        <th style="text-align: left;color: white; background-color: #215577; width:20%;">Accepted the Invite</th>
                        <th style="text-align: left;color: white; background-color: #215577; width:20%;">Declined the Invite</th>

                    </tr>
                    </table>
                """
                    #</div>        # <th style="text-align: left;color: white; background-color: #215577; ">Awaiting Response</th>
                for list_item in event.list_ids:
                    event_start = getattr(list_item, 'event_start_datetime', None)
                    event_end = getattr(list_item, 'event_end_datetime', None)
    
                    event_start_with_offset = event_start + timedelta(hours=5, minutes=30) if event_start else None
                    event_start_str = event_start_with_offset.strftime('%d-%m-%Y %H:%M') if event_start_with_offset else ""
                    #event_start_str = event_start.strftime('%d-%m-%Y %H:%M') if event_start else ""
                    event_end_with_offset = event_end + timedelta(hours=5, minutes=30) if event_end else None
                    event_end_str = event_end_with_offset.strftime('%d-%m-%Y %H:%M') if event_end_with_offset else ""
    
                    body_message += f"""
                    <table cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">
                    <tr>
                        <td style="border-left: 1px solid grey; border-right: 1px solid grey; border-bottom: 1px solid grey;width:20%;">{list_item.name}</td>
                        <td style="border-left: 1px solid grey; border-right: 1px solid grey; border-bottom: 1px solid grey;width:20%;">{event_start_str}</td>
                        <td style="border-left: 1px solid grey; border-right: 1px solid grey; border-bottom: 1px solid grey;width:20%;">{event_end_str}</td>
                        <td style="border-left: 1px solid grey; border-right: 1px solid grey; border-bottom: 1px solid grey;width:20%;"><a href="{base_url}/event/accept?event_id={event.id}&partner_id={partner.partner_id.id}&eventlist_id={list_item.id}&attendees_status={"accepted"}&state={"open"}" style="text-decoration: none; color: white; background-color: green; padding: 10px 15px; border-radius: 5px; display: inline-block;"><b>Accept</b></a></td>
                        <td style="border-left: 1px solid grey; border-right: 1px solid grey; border-bottom: 1px solid grey;width:20%;"><a href="{base_url}/event/decline?event_id={event.id}&partner_id={partner.partner_id.id}&eventlist_id={list_item.id}&attendees_status={"declined"}&state={"cancel"}" style="text-decoration: none; color: white; background-color: red; padding: 10px 15px; border-radius: 5px; display: inline-block;"><b>Decline</b></a></td>
                    
                    </tr></table>
                    """
                   # <td><a href="{base_url}/event/awaiting?event_id={event.id}&partner_id={partner.partner_id.id}&eventlist_id={list_item.id}&attendees_status={"awaiting"}&state={"open"}" style="text-decoration: none; color: white; background-color: orange; padding: 10px 15px; border-radius: 5px; display: inline-block;"><b>Awaiting</b></a></td>
    
                body_message += f"""
                
                <br/>
                <h3 style="text-align: center; color: #215577; margin-top: 20px;">Respond to All Invitations</h3>
                <table style="margin: 0 auto; text-align: center;">
                    <tr>
                        <td>
                            <a href="{base_url}/event/accept_all?event_id={event.id}&partner_id={partner.partner_id.id}&state=open" 
                               style="text-decoration: none; text-align:center; color: white; width:123px; background-color: #215577; padding: 10px 15px; border-radius: 5px; display: inline-block;">
                                <b>Accept All</b>
                            </a>
                        </td>
                        <td>
                            <a href="{base_url}/event/decline_all_form?event_id={event.id}&partner_id={partner.partner_id.id}&attendees_status={'declined'}&state={'cancel'}" 
                               style="text-decoration: none; text-align:center; width:123px; color: white; background-color: #215577; padding: 10px 15px; border-radius: 5px; display: inline-block;">
                                <b>Decline All</b>
                            </a>
                        </td>
                    </tr>
                </table>
                <table style="width: 100%;">
                <tr><td style="text-align:center;">
                    <t t-if="organizer_id">
                        <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
                    </t>
                </td></tr>

                <tr><td valign="top" style="font-size: 14px;">
                    <!-- CONTACT ORGANIZER -->
                    <t t-if="organizer_id">
                        <div>
                            <span style="font-weight:300;margin:10px 0px;color:#215577;">Questions about this event? Please contact the organizer:</span>
                    
                                                <ul style="list-style-type: square; color: #215577;">
                        
                            <li><strong>Organizer Name:</strong> {event.organizer_id.name or ''}</li>
                       
                            <li><strong>Email:</strong> 
                                {event.organizer_id.email or ''}
                            </li>
                       
                            <li><strong>Phone:</strong> {event.organizer_id.phone or ''}</li>
                       
                    </ul>
                    
                                            </div>
                                        </t>
                                    </td></tr>
                                    </table>
                <p>Looking forward to your presence!</p>
    """
                body = f"""
                 {body_message}
                
                <div style="text-align:center;width: 100%;">
                Sent by <strong">{event.company_id.name or 'Our Company'}</strong>
                """
                body += "</div>"
                
                # # Footer
                # body = f"""
                # {body_message}
                # <br/>
                # <div style="width: 375px; margin: 0px; padding: 0px; border:1px solid #215577; background-color: #F2F2F2; border-top-left-radius: 5px;border-bottom-right-radius: 5px;border-bottom-left-radius: 5px; border-top-right-radius: 5px; background-repeat: repeat no-repeat;">
                #     <h2 style="margin: 0px; padding: 3px 14px;  background-color: #215577;font-size: 14px; color: black;">
                #         <strong style="text-transform:uppercase;color:white;">{event.company_id.name or 'Our Company'}</strong>
                #     </h2>
                #
                # <div style="width: 375px; margin: 0px; background-color: #F2F2F2;">
                # """
                #
                # if event.company_id.phone:
                #     body += f"""
                #     <div style="padding-left: 12px;padding-top:5px;">
                #         <span style="color:#215577;"><b>Phone:</b>  </span> {event.company_id.phone}
                #     </div>
                #     """
                # if event.company_id.email:
                #     body += f"""
                #     <div style="padding-left: 12px;padding-top:5px;">
                #         <span style="color:#215577;"><b>Email:</b> </span> {event.company_id.email}
                #     </div>
                #     """
                # if event.company_id.website:
                #     body += f"""
                #     <div style="padding-left: 12px;padding-top:5px;padding-bottom:5px;">
                #         <span style="color:#215577;"><b>Web:</b> </span>  <a style="color: #215577;" href="{event.company_id.website}">{event.company_id.website}</a>
                #     </div>
                #     """
                # body += "</div><br/></div> "
    
                # Mail values
                mail_values = {
                    'subject': subject,
                    'body_html': body,
                    'email_to': partner.partner_id.email,
                    'email_from': event.company_id.email,
                    'auto_delete': True,
                }
    
                mail = self.env['mail.mail'].sudo().create(mail_values)
                mail.send()
                partner.invited = True
            # for partner in event.invite_partner_ids:  # Loop through each partner in the event
            #     for list_item in event.list_ids:  # Loop through each list item associated with the partner
            #         tracking_vals = {
            #                 'invitee_id': partner.partner_id.id,  # Use partner's name
            #                 'event_id': event.id,  # Link to the event
            #                 'eventlist_id': list_item.id,  # Link to the list item
            #             }
            #
            #             # Search for existing record with the same event and list item
            #         tracking_record = self.env['event.invite.track'].search([
            #                 ('event_id', '=', event.id),
            #                 ('eventlist_id', '=', list_item.id),
            #                 ('invitee_id', '=', partner.partner_id.id),
            #             ], limit=1)
            #
            #         if tracking_record:
            #                 # Update the existing record if found
            #             tracking_record.write(tracking_vals)
            #         else:
            #                 # Create a new record if none exists
            #             self.env['event.invite.track'].create(tracking_vals)
            records_to_create = []
            for partner in event.invite_partner_ids:
                for list_item in event.list_ids:
                    tracking_vals = {
                        'invitee_id': partner.partner_id.id,  # Use partner's name
                            'event_id': event.id,  # Link to the event
                            'eventlist_id': list_item.id,  # Link to the list item
                    }
                    tracking_record = self.env['event.invite.track'].search([
                         ('event_id', '=', event.id),
                            ('eventlist_id', '=', list_item.id),
                            ('invitee_id', '=', partner.partner_id.id),
                        ], limit=1)
            
                    if tracking_record:
                        tracking_record.write(tracking_vals)
                    else:
                        records_to_create.append(tracking_vals)
            
            # Create records in batch
            if records_to_create:
                self.env['event.invite.track'].create(records_to_create)


                
                
    def open_partner_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'event.partner.wizard',
            'name':'Add Event invite Partners'
,           'view_mode': 'form',
            'target': 'new',
            'context': {'default_event_id': self.id},
        }      
                
    @api.model
    def create(self, vals):
        # Optional validation for image on creation
        if 'image' in vals and vals['image']:
            self._validate_image(vals['image'])
        return super(Event, self).create(vals)

    def write(self, vals):
        # Optional validation for image on update
        if 'image' in vals and vals['image']:
            self._validate_image(vals['image'])
        
        previous_dates = { 'date_begin': self.date_begin, 'date_end': self.date_end }
        initial_list_ids = {rec.id: rec.name for rec in self.list_ids}
        initial_event_start_datetimes = {rec.id: rec.event_start_datetime for rec in self.list_ids}
        initial_event_end_datetimes = {rec.id: rec.event_end_datetime for rec in self.list_ids}


        # if 'date_begin' in vals or 'date_end' in vals:
        #     # Send notification emails to all registrations
        #     for event in self:
        #         registration_ids = event.registration_ids
        #         if registration_ids:
        #             self.send_notification_email(registration_ids)
        # return super(Event, self).write(vals)
        result = super(Event, self).write(vals)
        
        list_ids_changed = False
        for record in self:
            if 'date_begin' in vals or 'date_end' in vals or 'name' in vals or 'address_id' in vals or 'organizer_id' in vals:
                list_ids_changed = True
            else:
                for rec in record.list_ids:
                    if (rec.id in initial_list_ids and rec.name != initial_list_ids[rec.id]) or \
                       (rec.id in initial_event_start_datetimes and rec.event_start_datetime != initial_event_start_datetimes[rec.id]) or \
                       (rec.id in initial_event_end_datetimes and rec.event_end_datetime != initial_event_end_datetimes[rec.id]):
                        list_ids_changed = True
                        break
                    # if rec.id in initial_list_ids and rec.name != initial_list_ids[rec.id]:
                    #     list_ids_changed = True
                    #     break
    
            if list_ids_changed:
                registration_ids = record.registration_ids
                if registration_ids:
                    record.send_notification_email(registration_ids, previous_dates)

        # # Check if date_begin or date_end is being updated
        # if 'date_begin' in vals or 'date_end' in vals or 'name' in vals or 'address_id' in vals or 'organizer_id' in vals or 'list_ids.name' in vals:
        #     # Send notification emails to all registrations
        #     for event in self:
        #         registration_ids = event.registration_ids
        #         if registration_ids:
        #             self.send_notification_email(registration_ids, previous_dates)
        

        return result
    
    def send_notification_email(self, registration_ids, previous_dates):
    # Prepare the email template
        email_template_id = self.env.ref('event_inherit.event_subscription_update').id
        template = self.env['mail.template'].browse(email_template_id)
    
        for registration in registration_ids:
            if registration.partner_id.email and registration.state in ['draft','open']:  # Check if the partner has an email
                # Clone the email template for modification
                email_body = template.body_html
    
                # Replace event-level placeholders
                email_body = email_body.replace(
                    "${object.event_id.date_begin}",
                    self.date_begin.strftime('%B %d, %Y, %I:%M:%S %p')
                ).replace(
                    "${object.event_id.date_end}",
                    self.date_end.strftime('%B %d, %Y, %I:%M:%S %p')
                ).replace(
                    "${object.event_id.name}",
                    self.name
                ).replace(
                    "${object.event_id.address_id}",
                    self.address_id.name if self.address_id else "No Address"
                ).replace(
                    "${object.event_id.organizer_id}",
                    self.organizer_id.name if self.organizer_id else "Organizer Details not Available"
                )
    
                # Replace placeholders for each list_id record individually
                for line in self.list_ids:
                    email_body = email_body.replace(
                        f"${{object.list_ids.{line.id}.name}}",
                        line.name
                    ).replace(
                        f"${{object.list_ids.{line.id}.event_start_datetime}}",
                        line.event_start_datetime.strftime('%B %d, %Y, %I:%M:%S %p') if line.event_start_datetime else "No Start Date"
                    ).replace(
                        f"${{object.list_ids.{line.id}.event_end_datetime}}",
                        line.event_end_datetime.strftime('%B %d, %Y, %I:%M:%S %p') if line.event_end_datetime else "No End Date"
                    )
    
                # Send email with the updated body
                template.write({'body_html': email_body})
                template.send_mail(registration.id, force_send=True)

    
    # def send_notification_email(self, registration_ids, previous_dates):
    #     # Prepare the email template
    #     email_template_id = self.env.ref('event_inherit.event_subscription_update').id
    #     template = self.env['mail.template'].browse(email_template_id)
    #
    #     for registration in registration_ids:
    #         if registration.partner_id.email:  # Check if the partner has an email
    #             # Update the body_html to reflect the updated dates
    #             template.body_html = template.body_html.replace(
    #                 "${object.event_id.date_begin}",
    #                 self.date_begin.strftime('%B %d, %Y, %I:%M:%S %p')
    #             ).replace(
    #                 "${object.event_id.date_end}",
    #                 self.date_end.strftime('%B %d, %Y, %I:%M:%S %p')
    #             ).replace(
    #                 "${object.event_id.name}",
    #                 self.name
    #             ).replace(
    #                 "${object.event_id.address_id}",
    #                 self.address_id.name if self.address_id else "No Address"
    #             ).replace(
    #                 "${object.event_id.organizer_id}",
    #                 self.organizer_id.name if self.organizer_id else "Organizer Details not Available"
    #             ).replace(
    #                 "${object.list_ids.name}",
    #                 self.list_ids.name if self.list_ids else False
    #             ).replace(
    #                 "${object.event_id.list_ids.event_start_datetime}",
    #                 self.list_ids.event_start_datetime.strftime('%B %d, %Y, %I:%M:%S %p')
    #             ).replace(
    #                 "${object.event_id.list_ids.event_end_datetime}",
    #                 self.list_ids.event_end_datetime.strftime('%B %d, %Y, %I:%M:%S %p')
    #             )
    #             # Send email for each registration
    #             template.send_mail(registration.id, force_send=True)

    def _validate_image(self, image_data):
        try:
            image_decoded = base64.b64decode(image_data)
            Image.open(BytesIO(image_decoded))  # Validate it is an actual image
        except Exception:
            raise UserError(_("Uploaded file is not a valid image."))
                # Post a message in the chatter
                # event.message_post(
                #     body=body,
                #     subject=subject,
                #     message_type='notification',
                #     subtype_id=self.env.ref('mail.mt_note').id,
                
class EventPartnerWizard(models.TransientModel):
    _name = 'event.partner.wizard'
    _description = 'Add Partners to Event'

    partner_ids = fields.Many2many('res.partner', string="Partners",  domain=lambda self: self._get_partner_domain())
    event_id = fields.Many2one('event.event', string="Event", required=True)
    
    def _get_partner_domain(self):
        """
        Exclude partners already invited to the selected event.
        """
        if not self.event_id:
            return [("membership_state", "in", ["invoiced", "paid", "free"])]
        invited_partner_ids = self.env['event.partner.line'].search([
            ('event_id', '=', self.event_id.id)
        ]).mapped('partner_id.id')
        return [
            ("membership_state", "in", ["invoiced", "paid", "free"]),
            ('id', 'not in', invited_partner_ids)
        ]

    @api.onchange('event_id')
    def _onchange_event_id(self):
        """
        Update the partner domain dynamically based on the selected event.
        """
        if self.event_id:
            domain = self._get_partner_domain()
            return {'domain': {'partner_ids': domain}}
        
    def add_partners(self):
        for partner in self.partner_ids:
            self.env['event.partner.line'].create({
                'partner_id': partner.id,
                'event_id': self.event_id.id,
            })

                # )
                
class EventPartnerLine(models.Model):
    _name = 'event.partner.line'
    _description = 'Event Partner Line'

    partner_id = fields.Many2one('res.partner', string="Partner", required=True, domain=[("membership_state", "in", ["invoiced", "paid", "free"])])
    invited = fields.Boolean("Invited", default=False)
    event_id = fields.Many2one('event.event', string="Event", ondelete='cascade')
    
    @api.model
    def create(self, vals):
        # Check if the partner is already added to this event
        existing = self.search([
            ('partner_id', '=', vals.get('partner_id')),
            ('event_id', '=', vals.get('event_id'))
        ])
        if existing:
            # Skip creating if already exists
            return existing[0]
        return super(EventPartnerLine, self).create(vals)
    
class EventType(models.Model):
    _inherit = 'event.type'
    

    def _default_event_mail_type_ids(self):
        return [(0, 0,
                 {'notification_type': 'mail',
                  'interval_nbr': 0,
                  'interval_unit': 'now',
                  'interval_type': 'after_sub',
                  'template_ref': 'mail.template, %i' % self.env.ref('event.event_subscription').id,
                 }),
                (0, 0,
                 {'notification_type': 'mail',
                  'interval_nbr': 1,
                  'interval_unit': 'hours',
                  'interval_type': 'before_event',
                  'template_ref': 'mail.template, %i' % self.env.ref('event.event_reminder').id,
                 }),
                (0, 0,
                 {'notification_type': 'mail',
                  'interval_nbr': 3,
                  'interval_unit': 'days',
                  'interval_type': 'before_event',
                  'template_ref': 'mail.template, %i' % self.env.ref('event.event_reminder').id,
                 }),
                (0, 0,
                 {'notification_type': 'mail',
                  'interval_nbr': 1,
                  'interval_unit': 'days',
                  'interval_type': 'before_event',
                  'template_ref': 'mail.template, %i' % self.env.ref('event.event_registration_mail_template_badge').id,
                 }),
                
                
                
                
                ]