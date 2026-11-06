import csv
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model, login
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
import hmac
from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_GET
from .reminders import create_due_reminders

from .forms import AvatarForm, CommentForm, MilestoneForm, ProfileForm, ProjectForm, SignUpForm, TaskForm
from .models import CATEGORIES, Comment, Notification, Profile, Project, Task
from .permissions import (
    can_manage_project, owned_milestones, owned_projects, owned_tasks,
    toggleable_tasks, visible_projects, visible_tasks,
)

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


def notify_assignment(task, actor):
    """Tell the assignee about a task, unless they assigned it to themselves."""
    if task.assignee_id and task.assignee_id != actor.id:
        Notification.objects.create(
            user=task.assignee,
            message=f"{actor.get_username()} assigned you “{task.title}”",
            link=reverse("task_detail", args=[task.pk]),
        )


def notify_comment(task, author):
    """Tell the assignee and the project owner about a new comment."""
    people = {task.assignee_id: task.assignee, task.project.owner_id: task.project.owner}
    for uid, person in people.items():
        if person and uid != author.id:
            Notification.objects.create(
                user=person,
                message=f"{author.get_username()} commented on “{task.title}”",
                link=reverse("task_detail", args=[task.pk]),
            )


# ----------------------------------------------------------- sign up
def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Welcome! Your account is ready.")
        return redirect("dashboard")
    return render(request, "accounts/signup.html", {"form": form})


# -------------------------------------------------------------- dashboard
@login_required
def dashboard(request):
    now = timezone.now()
    week_ago = now - timedelta(days=7)
    tasks = visible_tasks(request.user)
    projects = visible_projects(request.user)

    done_qs = tasks.filter(is_done=True)
    done_this_week = done_qs.filter(completed_at__gte=week_ago).count()
    done_last_week = done_qs.filter(
        completed_at__gte=week_ago - timedelta(days=7), completed_at__lt=week_ago
    ).count()
    growth = round((done_this_week - done_last_week) * 100 / done_last_week) if done_last_week else 0

    pending_now = tasks.filter(is_done=False).count()
    pending_then = tasks.filter(created_at__lt=week_ago).filter(
        Q(completed_at__isnull=True) | Q(completed_at__gte=week_ago)
    ).count()

    # Completion rate at the end of each of the last 6 months
    labels, rates = [], []
    for back in range(5, -1, -1):
        start = _month_start(now, -back)
        end = now if back == 0 else _month_start(now, -back + 1)
        existing = tasks.filter(created_at__lt=end)
        total = existing.count()
        finished = existing.filter(is_done=True, completed_at__lt=end).count()
        labels.append(start.strftime("%b"))
        rates.append(round(finished * 100 / total) if total else 0)

    counts = dict(tasks.values_list("category").annotate(n=Count("id")))
    category_labels = [label for key, label in CATEGORIES if counts.get(key)]
    category_data = [counts[key] for key, _ in CATEGORIES if counts.get(key)]

    ctx = {
        "total_projects": projects.count(),
        "new_projects": projects.filter(created_at__gte=week_ago).count(),
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
        "recent_projects": projects.select_related("owner__profile").prefetch_related("tasks")[:5],
    }
    return render(request, "projects/dashboard.html", ctx)


# --------------------------------------------------------------- projects
class ProjectListView(LoginRequiredMixin, ListView):
    template_name = "projects/project_list.html"
    paginate_by = 10

    def get_queryset(self):
        qs = visible_projects(self.request.user).select_related("owner__profile").prefetch_related("tasks")
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
        return visible_projects(self.request.user).select_related("owner__profile").prefetch_related("tasks__assignee__profile")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        milestones = list(self.object.milestones.annotate(
            task_total=Count("tasks"), task_done=Count("tasks", filter=Q(tasks__is_done=True))))
        for m in milestones:
            m.percent = round(m.task_done * 100 / m.task_total) if m.task_total else (100 if m.is_completed else 0)
        ctx["milestones"] = milestones
        ctx["can_manage"] = can_manage_project(self.request.user, self.object)
        return ctx


class ProjectCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = "form.html"
    success_message = "Project created."
    extra_context = {"title": "New project"}

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_initial(self):
        return {"owner": self.request.user}

    def form_valid(self, form):
        if not form.instance.owner_id:
            form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("project_detail", args=[self.object.pk])


class ProjectUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = "form.html"
    success_message = "Changes saved."

    def get_queryset(self):
        return owned_projects(self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

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

    def get_queryset(self):
        return owned_projects(self.request.user)


# ------------------------------------------------------------- milestones
class MilestoneCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    form_class = MilestoneForm
    template_name = "form.html"
    success_message = "Milestone added."

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.project = get_object_or_404(owned_projects(request.user), pk=kwargs["project_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = f"New milestone for {self.project.name}"
        return ctx

    def form_valid(self, form):
        form.instance.project = self.project
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("project_detail", args=[self.project.pk])


class MilestoneUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    form_class = MilestoneForm
    template_name = "form.html"
    success_message = "Changes saved."
    extra_context = {"title": "Edit milestone"}

    def get_queryset(self):
        return owned_milestones(self.request.user)

    def get_success_url(self):
        return reverse("project_detail", args=[self.object.project_id])


class MilestoneDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    template_name = "confirm_delete.html"
    success_message = "Milestone deleted."

    def get_queryset(self):
        return owned_milestones(self.request.user)

    def get_success_url(self):
        return reverse("project_detail", args=[self.object.project_id])


@login_required
@require_POST
def milestone_toggle(request, pk):
    milestone = get_object_or_404(owned_milestones(request.user), pk=pk)
    milestone.is_completed = not milestone.is_completed
    milestone.save()
    return redirect(_safe_next(request, reverse("project_detail", args=[milestone.project_id])))


# ------------------------------------------------------------------ tasks
class TaskListView(LoginRequiredMixin, ListView):
    template_name = "projects/task_list.html"
    paginate_by = 15

    def get_queryset(self):
        qs = visible_tasks(self.request.user).select_related("project", "assignee__profile")
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
            all_projects=visible_projects(self.request.user).only("id", "name"),
            qs=params.urlencode(),
        )
        return ctx


class TaskDetailView(LoginRequiredMixin, DetailView):
    template_name = "projects/task_detail.html"
    context_object_name = "task"

    def get_queryset(self):
        return visible_tasks(self.request.user).select_related("project__owner", "assignee__profile", "milestone")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx["comments"] = self.object.comments.select_related("author__profile")
        ctx["comment_form"] = CommentForm()
        ctx["can_manage"] = can_manage_project(user, self.object.project)
        ctx["can_toggle"] = ctx["can_manage"] or self.object.assignee_id == user.id
        return ctx


class TaskCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = "form.html"
    success_message = "Task created."
    extra_context = {"title": "New task"}

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_initial(self):
        project = self.request.GET.get("project", "")
        return {"project": project} if project.isdigit() else {}

    def form_valid(self, form):
        response = super().form_valid(form)
        notify_assignment(self.object, self.request.user)
        return response

    def get_success_url(self):
        return reverse("project_detail", args=[self.object.project_id])


class TaskUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = "form.html"
    success_message = "Changes saved."

    def get_queryset(self):
        return owned_tasks(self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Edit task"
        return ctx

    def form_valid(self, form):
        reassigned = "assignee" in form.changed_data
        response = super().form_valid(form)
        if reassigned:
            notify_assignment(self.object, self.request.user)
        return response

    def get_success_url(self):
        return reverse("task_detail", args=[self.object.pk])


class TaskDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Task
    template_name = "confirm_delete.html"
    success_message = "Task deleted."

    def get_queryset(self):
        return owned_tasks(self.request.user)

    def get_success_url(self):
        return reverse("project_detail", args=[self.object.project_id])


@login_required
@require_POST
def task_toggle(request, pk):
    task = get_object_or_404(toggleable_tasks(request.user), pk=pk)
    task.is_done = not task.is_done
    task.save()
    return redirect(_safe_next(request, reverse("task_list")))


# --------------------------------------------------------------- comments
@login_required
@require_POST
def comment_add(request, pk):
    task = get_object_or_404(visible_tasks(request.user).select_related("project__owner", "assignee"), pk=pk)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.task, comment.author = task, request.user
        comment.save()
        notify_comment(task, request.user)
        messages.success(request, "Comment posted.")
    else:
        messages.error(request, "Write something before posting.")
    return redirect("task_detail", pk=task.pk)


@login_required
@require_POST
def comment_delete(request, pk):
    qs = Comment.objects.filter(task__in=visible_tasks(request.user))
    if not request.user.is_superuser:
        qs = qs.filter(Q(author=request.user) | Q(task__project__owner=request.user))
    comment = get_object_or_404(qs, pk=pk)
    task_pk = comment.task_id
    comment.delete()
    messages.success(request, "Comment deleted.")
    return redirect("task_detail", pk=task_pk)


# ---------------------------------------------------------------- reports
@login_required
def reports(request):
    now = timezone.now()
    tasks = visible_tasks(request.user)
    total = tasks.count()
    done = tasks.filter(is_done=True).count()
    overdue = tasks.filter(is_done=False, due_date__lt=now).select_related("project", "assignee__profile")
    projects = list(visible_projects(request.user).prefetch_related("tasks"))
    people = [
        u for u in User.objects.filter(is_active=True).select_related("profile")
        .annotate(
            open_n=Count("assigned_tasks", filter=Q(assigned_tasks__is_done=False, assigned_tasks__in=tasks)),
            done_n=Count("assigned_tasks", filter=Q(assigned_tasks__is_done=True, assigned_tasks__in=tasks)),
        )
        .order_by("username")
        if u.open_n or u.done_n
    ]
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
    for t in visible_tasks(request.user).select_related("project", "assignee"):
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
        "team": User.objects.filter(is_active=True).select_related("profile").order_by("username"),
    })


@login_required
@require_POST
def avatar_update(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    old_name = profile.avatar.name
    form = AvatarForm(request.POST, request.FILES, instance=profile)
    if form.is_valid():
        try:
            form.save()
        except OSError:  # the server's disk is read-only (for example on Vercel)
            messages.error(request, "Picture uploads are not available on this server yet.")
            return redirect("settings_page")
        if old_name and old_name != profile.avatar.name:
            profile.avatar.storage.delete(old_name)  # remove the previous picture's file
        messages.success(request, "Profile picture updated.")
    else:
        messages.error(request, form.errors["avatar"][0] if "avatar" in form.errors else "Could not upload that file.")
    return redirect("settings_page")


@login_required
@require_POST
def avatar_remove(request):
    profile = Profile.objects.filter(user=request.user).first()
    if profile and profile.avatar:
        profile.avatar.delete(save=True)
        messages.success(request, "Profile picture removed.")
    return redirect("settings_page")


@login_required
def search(request):
    q = request.GET.get("q", "").strip()
    projects = tasks = []
    if q:
        projects = visible_projects(request.user).filter(Q(name__icontains=q) | Q(description__icontains=q))[:20]
        tasks = visible_tasks(request.user).filter(title__icontains=q).select_related("project")[:30]
    return render(request, "projects/search.html", {"q": q, "projects": projects, "tasks": tasks})


@login_required
@require_POST
def notifications_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect(_safe_next(request, reverse("dashboard")))

@require_GET
def cron_send_reminders(request):
       secret = settings.CRON_SECRET
       sent = request.headers.get("Authorization", "")
       if not secret or not hmac.compare_digest(sent, f"Bearer {secret}"):
           return HttpResponseForbidden("Forbidden")
       created = create_due_reminders()
       return HttpResponse(f"{created} reminder(s) created.")