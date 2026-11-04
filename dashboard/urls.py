from django.urls import path

from . import views

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),

    # Projects
    path("projects/", views.ProjectListView.as_view(), name="project_list"),
    path("projects/new/", views.ProjectCreateView.as_view(), name="project_create"),
    path("projects/<int:pk>/", views.ProjectDetailView.as_view(), name="project_detail"),
    path("projects/<int:pk>/edit/", views.ProjectUpdateView.as_view(), name="project_update"),
    path("projects/<int:pk>/delete/", views.ProjectDeleteView.as_view(), name="project_delete"),

    # Milestones
    path("projects/<int:project_pk>/milestones/new/", views.MilestoneCreateView.as_view(), name="milestone_create"),
    path("milestones/<int:pk>/edit/", views.MilestoneUpdateView.as_view(), name="milestone_update"),
    path("milestones/<int:pk>/delete/", views.MilestoneDeleteView.as_view(), name="milestone_delete"),
    path("milestones/<int:pk>/toggle/", views.milestone_toggle, name="milestone_toggle"),

    # Tasks
    path("tasks/", views.TaskListView.as_view(), name="task_list"),
    path("tasks/new/", views.TaskCreateView.as_view(), name="task_create"),
    path("tasks/<int:pk>/", views.TaskDetailView.as_view(), name="task_detail"),
    path("tasks/<int:pk>/edit/", views.TaskUpdateView.as_view(), name="task_update"),
    path("tasks/<int:pk>/delete/", views.TaskDeleteView.as_view(), name="task_delete"),
    path("tasks/<int:pk>/toggle/", views.task_toggle, name="task_toggle"),

    # Comments
    path("tasks/<int:pk>/comment/", views.comment_add, name="comment_add"),
    path("comments/<int:pk>/delete/", views.comment_delete, name="comment_delete"),

    # Reports
    path("reports/", views.reports, name="reports"),
    path("reports/export/", views.report_export, name="report_export"),

    # Settings, search, notifications
    path("settings/", views.settings_page, name="settings_page"),
    path("settings/avatar/", views.avatar_update, name="avatar_update"),
    path("settings/avatar/remove/", views.avatar_remove, name="avatar_remove"),
    path("search/", views.search, name="search"),
    path("notifications/read/", views.notifications_read, name="notifications_read"),
    path("cron/send-reminders/", views.cron_send_reminders, name="cron_send_reminders"),  

]