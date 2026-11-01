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

    # Tasks
    path("tasks/", views.TaskListView.as_view(), name="task_list"),
    path("tasks/new/", views.TaskCreateView.as_view(), name="task_create"),
    path("tasks/<int:pk>/edit/", views.TaskUpdateView.as_view(), name="task_update"),
    path("tasks/<int:pk>/delete/", views.TaskDeleteView.as_view(), name="task_delete"),
    path("tasks/<int:pk>/toggle/", views.task_toggle, name="task_toggle"),

    # Reports
    path("reports/", views.reports, name="reports"),
    path("reports/export/", views.report_export, name="report_export"),

    # Settings, search, notifications
    path("settings/", views.settings_page, name="settings_page"),
    path("search/", views.search, name="search"),
    path("notifications/read/", views.notifications_read, name="notifications_read"),
]