# Common system intent for declared personal Arch hosts.

# Timeshift's cron entry needs both cronie installed explicitly and its vendor
# service enabled. Applying this link does not start or restart the service.
CopyFile "/etc/cron.d/timeshift-hourly"
CreateLink "/etc/systemd/system/multi-user.target.wants/cronie.service" "/usr/lib/systemd/system/cronie.service"
