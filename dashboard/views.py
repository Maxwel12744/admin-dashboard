from django.shortcuts import render

# Create your views here.
import csv
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import ProfileForm, ProjectForm, TaskForm
from .models import CATEGORIES, Notification, Project, Task

User = get_user_model()


# ---------------------------------------------------------------- helpers
def _month_start(dt, offset):
    """First moment of the month `offset` months from dt (negative = past)."""
    index = dt.year * 12 + (dt.month - 1) + offset
    return dt.replace(year=index // 12, month=index % 12 + 1, day=1,
                      hour=0, minute=0, second=0, microsecond=0)


def _safe_next(request, default):
    nxt = request.POST.get("next", "")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return nxt
    return default


# -------------------------------------------------------------- dashboard
@login_required
def dashboard(request):
    now = timezone.now()
    week_ago = now - timedelta(days=7)

    done_qs = Task.objects.filter(is_done=True)
    done_this_week = done_qs.filter(completed_at__gte=week_ago).count()
    done_last_week = done_qs.filter(
        completed_at__gte=week_ago - timedelta(days=7), completed_at__lt=week_ago
    ).count()
    growth = round((done_this_week - done_last_week) * 100 / done_last_week) if done_last_week else 0

    pending_now = Task.objects.filter(is_done=False).count()
    pending_then = Task.objects.filter(created_at__lt=week_ago).filter(
        Q(completed_at__isnull=True) | Q(completed_at__gte=week_ago)
    ).count()

    # Completion rate at the end of each of the last 6 months
    labels, rates = [], []
    for back in range(5, -1, -1):
        start = _month_start(now, -back)
        end = now if back == 0 else _month_start(now, -back + 1)
        existing = Task.objects.filter(created_at__lt=end)
        total = existing.count()
        finished = existing.filter(is_done=True, completed_at__lt=end).count()
        labels.append(start.strftime("%b"))
        rates.append(round(finished * 100 / total) if total else 0)

    counts = dict(Task.objects.values_list("category").annotate(n=Count("id")))
    category_labels = [label for key, label in CATEGORIES if counts.get(key)]
    category_data = [counts[key] for key, _ in CATEGORIES if counts.get(key)]

    ctx = {
        "total_projects": Project.objects.count(),
        "new_projects": Project.objects.filter(created_at__gte=week_ago).count(),
        "completed_tasks": done_qs.count(),
        "growth": growth,
        "pending_tasks": pending_now,
        "pending_delta": pending_now - pending_then,
        "team_members": User.objects.filter(is_active=True).count(),
        "new_members": User.objects.filter(is_active=True, date_joined__gte=week_ago).count(),
        "progress_labels": labels,
        "progress_data": rates,
        "category_labels": category_labels,
        "category_data": category_data,
        "recent_projects": Project.objects.prefetch_related("tasks")[:5],
    }
    return render(request, "projects/dashboard.html", ctx)


# --------------------------------------------------------------- projects
class ProjectListView(LoginRequiredMixin, ListView):
    template_name = "projects/project_list.html"
    paginate_by = 10

    def get_queryset(self):
        qs = Project.objects.select_related("owner").prefetch_related("tasks")
        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "")
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop("page", None)
        ctx.update(q=self.request.GET.get("q", ""), status=self.request.GET.get("status", ""),
                   statuses=Project.Status.choices, qs=params.urlencode())
        return ctx


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "projects/project_detail.html"

    def get_queryset(self):
        return Project.objects.select_related("owner").prefetch_related("tasks__assignee")


class ProjectCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = "form.html"
    success_message = "Project created."
    extra_context = {"title": "New project"}

    def get_initial(self):
        return {"owner": self.request.user}

    def get_success_url(self):
        return reverse("project_detail", args=[self.object.pk])


class ProjectUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = "form.html"
    success_message = "Changes saved."

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = f"Edit {self.object.name}"
        return ctx

    def get_success_url(self):
        return reverse("project_detail", args=[self.object.pk])


class ProjectDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Project
    template_name = "confirm_delete.html"
    success_url = reverse_lazy("project_list")
    success_message = "Project deleted."


# ------------------------------------------------------------------ tasks
class TaskListView(LoginRequiredMixin, ListView):
    template_name = "projects/task_list.html"
    paginate_by = 15

    def get_queryset(self):
        qs = Task.objects.select_related("project", "assignee")
        g = self.request.GET
        if q := g.get("q", "").strip():
            qs = qs.filter(title__icontains=q)
        if g.get("state") == "open":
            qs = qs.filter(is_done=False)
        elif g.get("state") == "done":
            qs = qs.filter(is_done=True)
        if g.get("category"):
            qs = qs.filter(category=g["category"])
        if g.get("project", "").isdigit():
            qs = qs.filter(project_id=g["project"])
        if g.get("mine"):
            qs = qs.filter(assignee=self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop("page", None)
        ctx.update(
            q=self.request.GET.get("q", ""),
            state=self.request.GET.get("state", ""),
            category=self.request.GET.get("category", ""),
            project_id=self.request.GET.get("project", ""),
            mine=self.request.GET.get("mine", ""),
            categories=CATEGORIES,
            all_projects=Project.objects.only("id", "name"),
            qs=params.urlencode(),
        )
        return ctx


class TaskCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = "form.html"
    success_message = "Task created."
    extra_context = {"title": "New task"}

    def get_initial(self):
        project = self.request.GET.get("project", "")
        return {"project": project} if project.isdigit() else {}

    def form_valid(self, form):
        response = super().form_valid(form)
        task = self.object
        if task.assignee and task.assignee != self.request.user:
            Notification.objects.create(
                user=task.assignee,
                message=f"{self.request.user.get_username()} assigned you “{task.title}”",
                link=reverse("project_detail", args=[task.project_id]),
            )
        return response

    def get_success_url(self):
        return reverse("project_detail", args=[self.object.project_id])


class TaskUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = "form.html"
    success_message = "Changes saved."

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Edit task"
        return ctx

    def get_success_url(self):
        return reverse("project_detail", args=[self.object.project_id])


class TaskDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Task
    template_name = "confirm_delete.html"
    success_message = "Task deleted."

    def get_success_url(self):
        return reverse("project_detail", args=[self.object.project_id])


@login_required
@require_POST
def task_toggle(request, pk):
    task = get_object_or_404(Task, pk=pk)
    task.is_done = not task.is_done
    task.save()
    return redirect(_safe_next(request, reverse("task_list")))


# ---------------------------------------------------------------- reports
@login_required
def reports(request):
    today = timezone.localdate()
    total = Task.objects.count()
    done = Task.objects.filter(is_done=True).count()
    overdue = Task.objects.filter(is_done=False, due_date__lt=today).select_related("project", "assignee")
    projects = list(Project.objects.prefetch_related("tasks"))
    people = (
        User.objects.filter(is_active=True)
        .annotate(
            open_n=Count("assigned_tasks", filter=Q(assigned_tasks__is_done=False)),
            done_n=Count("assigned_tasks", filter=Q(assigned_tasks__is_done=True)),
        )
        .order_by("username")
    )
    ctx = {
        "total_tasks": total,
        "done_tasks": done,
        "completion_rate": round(done * 100 / total) if total else 0,
        "overdue_tasks": overdue,
        "project_labels": [p.name for p in projects],
        "project_progress": [p.progress for p in projects],
        "people": people,
        "people_labels": [u.get_username() for u in people],
        "people_open": [u.open_n for u in people],
        "people_done": [u.done_n for u in people],
    }
    return render(request, "projects/reports.html", ctx)


@login_required
def report_export(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="tasks.csv"'
    writer = csv.writer(response)
    writer.writerow(["Project", "Task", "Category", "Priority", "Assignee", "Due date", "Completed"])
    for t in Task.objects.select_related("project", "assignee"):
        writer.writerow([
            t.project.name, t.title, t.get_category_display(), t.get_priority_display(),
            t.assignee.get_username() if t.assignee else "", t.due_date or "",
            "yes" if t.is_done else "no",
        ])
    return response


# ---------------------------------------------------------- settings/search
@login_required
def settings_page(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("settings_page")
    return render(request, "projects/settings.html", {
        "form": form,
        "team": User.objects.filter(is_active=True).order_by("username"),
    })


@login_required
def search(request):
    q = request.GET.get("q", "").strip()
    projects = tasks = []
    if q:
        projects = Project.objects.filter(Q(name__icontains=q) | Q(description__icontains=q))[:20]
        tasks = Task.objects.filter(title__icontains=q).select_related("project")[:30]
    return render(request, "projects/search.html", {"q": q, "projects": projects, "tasks": tasks})


@login_required
@require_POST
def notifications_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect(_safe_next(request, reverse("dashboard")))