from odoo import models, fields, api

class ActivityDashboard(models.Model):
    _name = 'activity.dashboard'
    _description = 'Activity Dashboard'

    # Fields for the sidebar filters
    activity_type_filter = fields.Many2many('activity.tag', string="Activity Type")
    assigned_to_filter = fields.Many2many('res.users', string="Assigned To")
    
    # Filtered activities count
    completed_activities = fields.Integer(string='Completed Activities', compute='_compute_completed_activities')

    @api.model
    def get_users(self):
        return self.env['res.users'].search([])
        
    def _compute_completed_activities(self):
        for record in self:
            record.completed_activities = self.env['mail.activity'].search_count([
                ('state', '=', 'done'),
                ('active', '=', False)  # Ensure that completed activities are counted
            ])

    def action_apply_filters(self):
        # Apply filters based on Activity Type and Assigned To
        domain = []

        if self.activity_type_filter:
            domain.append(('activity_type_id', 'in', self.activity_type_filter.ids))
        
        if self.assigned_to_filter:
            domain.append(('user_id', 'in', self.assigned_to_filter.ids))
        
        # If no filters are selected, it will return all activities
        if not domain:
            domain = [('active', '=', True)]  # Or return all activities
        
        # Return filtered activities based on the selected filters
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mail.activity',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': domain,  # Apply the filters in the domain
        }

