@echo off
cd /d "C:\Users\pc\Desktop\web developement\admin-dashboard"
"venv\Scripts\python.exe" manage.py send_due_reminders >> reminders.log 2>&1