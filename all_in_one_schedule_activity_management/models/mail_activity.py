from collections import defaultdict
from odoo import fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    keep_done = fields.Boolean(
        string="Keep Done",
        help="If checked, the activity remains in the system after being marked as done."
    )
    
class MailActivity(models.Model):
    """This class is used to inherit the mail.activity model"""
    _inherit = "mail.activity"

    state = fields.Selection(
        [
            ("overdue", "Overdue"), ("today", "Today"), ("planned", "Planned"),
            ("cancel", "Cancelled"),
        ], 
        "State", compute="_compute_state", store=True,
        help="State for the activity",
    )
    active = fields.Boolean("Active", default=True, help="The record make Active")
    activity_type = fields.Many2many(
        "activity.tag", string="Activity Type", help="Activity type"
    )

    def _compute_state(self):
        """Compute the state of the activity based on its deadline"""
        today = fields.Date.today()
        for rec in self:

            if rec.active is False:
                rec.state = "done"
                continue

            if rec.date_deadline < today:
                rec.state = 'overdue'
            elif rec.date_deadline == today:
                rec.state = 'today'
            else:
                rec.state = 'planned'

    def action_mail_on_due_date(self):
        """This function is used to send mails on due date"""
        activity_email = self.env["mail.activity"].search([])
        notification_on_date = (
            self.env["ir.config_parameter"].sudo().get_param("notify_on_due_date")
        )
        notification_on_expiry = (
            self.env["ir.config_parameter"].sudo().get_param("notify_on_expiry")
        )
        for rec in activity_email:
            if notification_on_expiry:
                if rec.date_deadline < fields.Date.today():
                    self.env["mail.mail"].sudo().create(
                        {
                            "email_from": self.env.company.email,
                            "author_id": self.env.user.partner_id.id,
                            "body_html": "Hello <br> You missed the %s activity for the document %s </br>"
                            % (rec.activity_type_id.name, rec.res_name),
                            "subject": "%s Activity missed" % rec.activity_type_id.name,
                            "email_to": rec.user_id.email,
                        }
                    ).send(auto_commit=False)
            if notification_on_date:
                if rec.date_deadline == fields.Date.today():
                    self.env["mail.mail"].sudo().create(
                        {
                            "email_from": self.env.company.email,
                            "author_id": self.env.user.partner_id.id,
                            "body_html": "Hello <br> Today is your %s activity for the document %s </br>"
                            % (rec.activity_type_id.name, rec.res_name),
                            "subject": "Today %s Activity" % rec.activity_type_id.name,
                            "email_to": rec.user_id.email,
                        }
                    ).send(auto_commit=False)

    def action_activity_cancel(self):
        """Cancel the activity"""
        for rec in self:
            if rec.state == "cancel":
                raise UserError(_("You Can't Cancel this activity %s") % rec.res_name)
            else:
                rec.action_cancel()

    def action_activity_done(self):
        """Mark activity as done"""
        for rec in self:
            if rec.state == "done":
                raise UserError(_("You Can't Mark this activity %s as Done") % rec.res_name)
            else:
                rec.state = "done"
                rec.active = False

    def get_activity_count(self):
        """Return the count of different activities based on state"""
        activity = self.env["mail.activity"]
        # all_activity = activity.search([])
        planned = activity.search([("state", "=", "planned"), ("active", "=", True)])
        overdue = activity.search([("state", "=", "overdue"), ("active", "=", True)])
        today = activity.search([("state", "=", "today"), ("active", "=", True)])
        done = activity.search([("active", "=", False)])
        # cancel = activity.search([("state", "=", "cancel")])

        # all_activity = planned | overdue | today | done
        return {
            "len_all": len(planned + overdue + today + done),
            "len_overdue": len(overdue),
            "len_planned": len(planned),
            "len_today": len(today),
            "len_done": len(done),
            # "len_cancel": len(cancel),
        }

    def get_activity(self, id):
        """Fetch the activity based on ID"""
        activity = self.env['mail.activity'].browse(id)  # Use browse for direct access
        if activity.exists():  # Ensure the activity record exists
            return {
                'model': activity.res_model,  # This is the model related to the activity (e.g., 'res.partner')
                'res_id': activity.res_id,  # This is the ID of the record related to the activity
            }
        else:
            return {}  # Return an empty dict if the activity doesn't exist

    def _action_done(self, feedback=False, attachment_ids=None):
        """Mark activity as done, handling missing or archived records."""
        messages = self.env["mail.message"]
        next_activities_values = []
        attachments = self.env["ir.attachment"].search_read(
            [("res_model", "=", self._name), ("res_id", "in", self.ids)],
            ["id", "res_id"]
        )
        activity_attachments = defaultdict(list)
        for attachment in attachments:
            activity_id = attachment["res_id"]
            activity_attachments[activity_id].append(attachment["id"])

        for activity in self:
            _logger.info(f"Checking activity {activity.id} - State: {activity.state}, Active: {activity.active}")

            # Ensure the activity exists and is active before performing actions
            if not activity.exists() or not activity.active:
                _logger.error(f"Activity {activity.id} does not exist or is archived. Skipping operation.")
                raise UserError(_("This activity is no longer available or has been archived."))

            # Prevent activity from being deleted while processing
            if activity.state in ['done', 'cancel']:
                _logger.error(f"Activity {activity.id} has already been processed (done/cancelled). Skipping operation.")
                raise UserError(_("This activity has already been marked as done or cancelled."))

            # Handle the chaining of next activities (if needed)
            if activity.chaining_type == "trigger":
                vals = activity.with_context(
                    activity_previous_deadline=activity.date_deadline
                )._prepare_next_activity_values()
                next_activities_values.append(vals)

            # Post a message on the activity before deleting it
            records_sudo = self.env[activity.res_model].sudo().browse(activity.res_id)
            activity_message = records_sudo.message_post_with_source(
                "mail.message_activity_done",
                attachment_ids=attachment_ids,
                author_id=self.env.user.partner_id.id,
                render_values={
                    "activity": activity,
                    "feedback": feedback,
                    "display_assignee": activity.user_id != self.env.user,
                },
                mail_activity_type_id=activity.activity_type_id.id,
                subtype_xmlid='mail.mt_activities',
            )

            # Attachments handling
            attachment_ids = (attachment_ids or []) + activity_attachments.get(activity.id, [])
            if attachment_ids:
                activity.attachment_ids = attachment_ids

            # Link attachments to the message
            message_attachments = self.env["ir.attachment"].browse(activity_attachments[activity.id])
            if message_attachments:
                message_attachments.write({
                    "res_id": activity_message.id,
                    "res_model": activity_message._name,
                })
                activity_message.attachment_ids = message_attachments
            messages += activity_message

        next_activities = self.env['mail.activity']
        if next_activities_values:
            next_activities = self.env['mail.activity'].create(next_activities_values)

        # Archive activities
        self.action_archive()  # Archive activities by default
        
        # Mark the state of activities as done and set active to False (archived)
        for rec in self:
            rec.state = "done"
            rec.active = False  # Mark as archived

        return messages, next_activities

    def action_cancel(self):
        """Cancel activity"""
        for rec in self:
            rec.state = "cancel"

    # Add custom method to handle filtering by state, priority, etc.
    def get_filtered_activities(self, state=None, assigned_to=None):
        domain = []

        if state:
            domain.append(('state', '=', state))

        if assigned_to:
            domain.append(('user_id', '=', assigned_to))

        activities = self.search(domain)

        result = []

        for activity in activities:

            # ---- ORIGIN NAME FETCH ----
            origin_name = ""
            if activity.res_id and activity.res_model:
                try:
                    record = self.env[activity.res_model].browse(activity.res_id)
                    if record.exists():
                        origin_name = record.display_name
                except Exception:
                    origin_name = ""

            result.append({
                "id": activity.id,
                "display_name": activity.display_name,
                "activity_type_id": (activity.activity_type_id.id, activity.activity_type_id.name),
                "user_id": (activity.user_id.id, activity.user_id.name),
                "due_date": activity.date_deadline,
                "state": activity.state,
                "create_date": activity.create_date,
                "write_date": activity.write_date,
                "res_id": activity.res_id,
                "res_model": activity.res_model,
                "origin_name": origin_name,   # <-- IMPORTANT
            })

        return result

