# Hospital Admin Dashboard — Fix Plan (TODO)

## Steps

- [x] 1. Add dedicated `/hospital-admin/dashboard` Flask route in `app.py` with real DB data injection
- [x] 2. Add the route to the auto-route generator skip list in `app.py`
- [x] 3. Update `templates/hospital-admin/dashboard.html` to bind real data (KPIs, banner, tables, charts)
- [x] 4. Update `static/js/dashboard.js` to make charts data-driven (read from injected JSON)
- [x] 5. Test the route renders correctly with real data and N/A placeholders
