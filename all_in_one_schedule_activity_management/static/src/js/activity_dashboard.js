/** @odoo-module **/

import { Component, onWillStart, useState} from "@odoo/owl";
import { session } from "@web/session";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
// import { jsonrpc } from "@web/core/network/rpc_service";
import { rpc } from "@web/core/network/rpc";

class ActivityDashboard extends Component {
     static template = 'ActivityDashboard';
    setup() {
        super.setup();

        this.orm = useService("orm");
        this.activity_types = [];
        this.manage_activities = useState({
            len_all: 0,
            len_planned: 0,
            len_today: 0,
            len_overdue: 0,
            len_done: 0,
            // len_cancel: 0,

            planned_activity: [],
            today_activity: [],
            overdue_activity: [],
            done_activity: [],
            // cancelled_activity: [],
        });
        this.users = [];

        // 🔴 CRITICAL — bind handlers
        this.filter_activity_type = this.filter_activity_type.bind(this);
        this.filter_assigned_to = this.filter_assigned_to.bind(this);
        this.click_view = this.click_view.bind(this);
        this.click_origin_view = this.click_origin_view.bind(this);

        onWillStart(this.willStart);
    }

    async willStart() {
        this.title = 'Dashboard';
        await this.render_dashboards();
        await this.fetch_assigned_users(); 
        await this.load_activity_types();
    }

    async load_activity_types() {
        this.activity_types = await this.orm.searchRead(
            "mail.activity.type",
            [],
            ["name"]
        );
    }

    async addOriginNames(records) {
        const modelMap = {};

        // group ids by model
        for (const rec of records) {
            if (rec.res_model && rec.res_id) {
                if (!modelMap[rec.res_model]) {
                    modelMap[rec.res_model] = new Set();
                }
                modelMap[rec.res_model].add(rec.res_id);
            }
        }

        const nameMap = {};

        // fetch display names per model
        for (const model in modelMap) {
            const ids = [...modelMap[model]];
            const rows = await this.orm.read(model, ids, ["display_name"]);
            for (const r of rows) {
                nameMap[`${model}_${r.id}`] = r.display_name;
            }
        }

        // attach origin_name
        for (const rec of records) {
            rec.origin_name = nameMap[`${rec.res_model}_${rec.res_id}`] || "";
        }

        return records;
    }

    async render_dashboards() {
        // 1. Get counts from your custom method
        const counts = await rpc('/web/dataset/call_kw', {
            model: 'mail.activity',
            method: 'get_activity_count',
            args: [[]],
            kwargs: {},
        });
    
        console.log("Raw counts:", counts);
    
        this.manage_activities = {
            len_all:     Number(counts.len_all     || 0),
            len_planned: Number(counts.len_planned || 0),
            len_today:   Number(counts.len_today   || 0),
            len_overdue: Number(counts.len_overdue || 0),
            len_done:    Number(counts.len_done    || 0),
            // len_cancel:  Number(counts.len_cancel  || 0),   // if you have this key
            // Add any other keys your Python method returns
        };
    
        console.log("Activity counts from RPC:", counts);
        console.log("Processed manage_activities:", this.manage_activities);
    
        // Fetch records only if you really need them displayed in tables
        let today = await this.orm.searchRead(
            "mail.activity",
            [["state", "=", "today"]],
            ["display_name", "activity_type_id", "user_id", "date_deadline", "state", "create_date", "write_date","res_id","res_model"],  // Removed source_name
            { limit: 50 }
        );           
        this.manage_activities.today_activity = await this.addOriginNames(today);
        
        let planned = await this.orm.searchRead(
            "mail.activity",
            [["state", "=", "planned"]],
            ["display_name","activity_type_id","user_id","date_deadline","state","create_date","write_date","res_id","res_model"],
            { limit: 50 }
        );
        this.manage_activities.planned_activity = await this.addOriginNames(planned);

        // Fetch Overdue Activities
        let overdue = await this.orm.searchRead(
            "mail.activity",
            [["state", "=", "overdue"]],
            ["display_name", "activity_type_id", "user_id", "date_deadline", "state", "create_date", "write_date","res_id","res_model"],
            { limit: 50 }
        );
        this.manage_activities.overdue_activity = await this.addOriginNames(overdue);
    
        // Fetch Completed Activities
        let done = await this.orm.searchRead(
            "mail.activity",
            [
                ["active", "=", false],
                ["state", "!=", "cancel"]
            ],
            ["display_name", "activity_type_id", "user_id", "date_deadline", "state", "create_date", "write_date","res_id","res_model"],
            { context: { active_test: false } }
        );
        this.manage_activities.done_activity = await this.addOriginNames(done);
    
        // Fetch Cancelled Activities
        // let cancelled = await this.orm.searchRead(
        //     "mail.activity",
        //     [["state", "=", "cancelled"]],
        //     ["display_name", "activity_type_id", "user_id", "date_deadline", "state", "create_date", "write_date","res_id","res_model"],
        //     { limit: 50 }
        // );
        // this.manage_activities.cancelled_activity = await this.addOriginNames(cancelled);
    
        // console.log("Planned Activities:", this.manage_activities.planned_activity);
        // console.log("Overdue Activities:", this.manage_activities.overdue_activity);
        // console.log("Completed Activities:", this.manage_activities.done_activity);
        // console.log("Cancelled Activities:", this.manage_activities.cancelled_activity);
    }
    
    // Fetch the assigned users dynamically
    async fetch_assigned_users() {
        try {
            const users = await this.orm.searchRead(
                "res.users",  // Fetch from 'res.users' model
                [],
                ["name", "id"],
                { limit: 100 }
            );
            this.users = users;
        } catch (error) {
            console.error("Error fetching users:", error);
        }
    }

    // Filter by Activity Type
    filter_activity_type(typeId) {
        console.log("Filtering by Activity Type: " + typeId);
        this.fetch_filtered_activities({ typeId });
    }

    // Filter by Assigned To
    filter_assigned_to(user) {
        console.log("Filtering by Assigned To: " + user);
        this.fetch_filtered_activities({ user });
    }

    async fetch_filtered_activities(filters) {

        let domain = [];
        console.log(filters)
        const field=["display_name","activity_type_id","user_id","date_deadline","state","create_date","write_date","res_id","res_model"];

        if (filters.typeId) {
            domain.push(["activity_type_id", "in", [filters.typeId]]);
            console.log("typeId",domain)
        }

        if (filters.user && filters.user !== "All") {
            domain.push(["user_id", "=", filters.user]);
            console.log("user",domain)
        }

        const activities = await this.orm.searchRead(
            "mail.activity",
           domain,
            field,
            {}
        );

        const doneDomain = [...domain, ["active", "=", false]];
        const doneActivities = await this.orm.searchRead(
            "mail.activity",
            doneDomain,
            field,
            { context: { active_test: false } }  // <-- KEY: bypass active filter
        );
        
        console.log(activities)
        console.log(doneActivities)
       
            const planned = activities.filter(a => a.state === "planned");
            const today   = activities.filter(a => a.state === "today");
            const overdue = activities.filter(a => a.state === "overdue");
            // const done    = doneActivities.filter(a => a.state === "done");

            this.manage_activities.planned_activity = await this.addOriginNames(planned);
            this.manage_activities.today_activity = await this.addOriginNames(today);
            this.manage_activities.overdue_activity = await this.addOriginNames(overdue);
            this.manage_activities.done_activity = await this.addOriginNames(doneActivities);

            this.manage_activities.len_planned = planned.length;
            this.manage_activities.len_today = today.length;
            this.manage_activities.len_overdue = overdue.length;
            this.manage_activities.len_done = doneActivities.length;

            this.render();

    }

    click_view(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        if (!id) {
            console.warn("No id received");
            return;
        }
    
        this.env.services.action.doAction({
            type: 'ir.actions.act_window',
            name: 'All Activity',
            res_model: 'mail.activity',
            res_id: id,                // OPEN RECORD
            views: [[false, 'form']],
            target: 'new'
        });
    }
    

    // click_view(e) {
    //     const id = e.target.value;
    //     this.env.services.action.doAction({
    //         type: 'ir.actions.act_window',
    //         name: 'All Activity',
    //         res_model: 'mail.activity',
    //         domain: [['id', '=', id]],
    //         views: [ [false, 'form']],
    //         view_mode: 'list,form',
    //         target: 'new'
    //     });
    // }

    async click_origin_view(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        if (!id) return;

        // read activity to get target document
        const [activity] = await this.orm.read(
            "mail.activity",
            [id],
            ["res_model", "res_id"]
        );

        if (!activity.res_model || !activity.res_id) {
            console.warn("Activity has no linked document");
            return;
        }

        this.env.services.action.doAction({
            type: "ir.actions.act_window",
            res_model: activity.res_model,
            res_id: activity.res_id,
            views: [[false, "form"]],
            target: "current",
        });
    }


    // all_activity(e) {
    //     e.stopPropagation();
    //     e.preventDefault();
    //     this.env.services.action.doAction({
    //         type: 'ir.actions.act_window',
    //         name: 'All Activity',
    //         res_model: 'mail.activity',
    //         domain: [],
    //         views: [[false, 'list'], [false, 'form']],
    //         view_mode: 'list',
    //         target: 'current'
    //     });
    // }

    planned_activity(e) {
        e.stopPropagation();
        e.preventDefault();
        this.env.services.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Planned Activity',
            res_model: 'mail.activity',
            domain: [['state', '=', 'planned']],
            views: [[false, 'list'], [false, 'form']],
            view_mode: 'list',
            target: 'current'
        });
    }

    done_activity(e) {
        e.stopPropagation();
        e.preventDefault();
        this.env.services.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Done Activity',
            res_model: 'mail.activity',
            domain: [['active', '=', false]],
            views: [[false, 'list'], [false, 'form']],
            view_mode: 'list',
            target: 'current'
        });
    }
    today_activity(e) {
        e.stopPropagation();
        e.preventDefault();
        this.env.services.action.doAction({
            type: 'ir.actions.act_window',
            name: "Today's Activities",
            res_model: 'mail.activity',
            domain: [['state', '=', 'today']],
            views: [[false, 'list'], [false, 'form']],
            view_mode: 'list',
            target: 'current'
        });
    }
    overdue_activity(e) {
        e.stopPropagation();
        e.preventDefault();
        this.env.services.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Overdue Activity',
            res_model: 'mail.activity',
            domain: [['state', '=', 'overdue']],
            views: [[false, 'list'], [false, 'form']],
            view_mode: 'list',
            target: 'current'
        });
    }
    // cancelled_activity(e) {
    //     e.stopPropagation();
    //     e.preventDefault();
    //     this.env.services.action.doAction({
    //         type: 'ir.actions.act_window',
    //         name: "Today's Activity",
    //         res_model: 'mail.activity',
    //         domain: [['state', '=', 'cancel']],
    //         views: [[false, 'list'], [false, 'form']],
    //         view_mode: 'list',
    //         target: 'current'
    //     });
    // }
    // activity_type(e) {
    //     e.stopPropagation();
    //     e.preventDefault();
    //    this.env.services.action.doAction({
    //         type: 'ir.actions.act_window',
    //         name: "Today's Activity",
    //         res_model: 'mail.activity.type',
    //         views: [[false, 'list'], [false, 'form']],
    //         view_mode: 'list',
    //         target: 'current'
    //     });
    // }
}

registry.category("actions").add("activity_dashboard", ActivityDashboard);
// export default ActivityDashboard;