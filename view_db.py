import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "admin-dashboard.settings")
django.setup()

from admin_dashboard.models import ContactMessage

messages = ContactMessage.objects.all()

if not messages:
    print("No messages yet.")
else:
    print(f"{messages.count()} message(s)\n")
    for m in messages:
        print("-" * 50)
        print(f"ID:      {m.id}")
        print(f"From:    {m.name} <{m.email}>")
        print(f"Date:    {m.created:%Y-%m-%d %H:%M}")
        print(f"Message: {m.message}")
    print("-" * 50)
