# TODO - Frontend Notifications UI

## Goal
Implement ONLY the missing frontend notification layer.

## Steps
- [ ] Inspect existing notification read endpoint (accounts/urls.py, accounts/views.py)
- [ ] If none exists: create minimal endpoint POST /notifications/<notification_id>/read/ (login required, only recipient)
- [ ] Update base template with bell icon + unread badge + dropdown UI + empty state
- [ ] Add WebSocket client to customer_dashboard.html and provider_dashboard.html:
  - [ ] connect to /ws/notifications/
  - [ ] send {"action":"get_latest"}
  - [ ] handle notifications.latest and notifications.new
- [ ] Implement realtime dropdown rendering & badge updates (max 20, newest first)
- [ ] Implement mark-as-read on notification item click only
- [ ] Manual testing checklist and verification results

