# MediChain — Analytics Page Fix + Real DB Data

## Plan Steps

### 1. Backend (app.py)

- [x] Add `period` query param (`all` / `12m` / `6m` / `30d`) to `system_admin_analytics()`
- [x] Apply period filter to registration trend, city distribution, recent hospitals
- [x] Include system admin count in role data
- [x] Pass `selected_period` to template (success + exception renders)

### 2. Template (templates/system-admin/analytics.html)

- [x] Wire date-range `<select>` to reload with `?period=` param (preserve selection)
- [x] Wire "Export Report" button to `exportAnalyticsReport()`
- [x] Include System Admins in roles JSON for role chart

### 3. Frontend JS (static/js/dashboard.js)

- [x] Add `exportAnalyticsReport()` — download KPIs + recent hospitals table as CSV
- [x] Add `onAnalyticsPeriodChange()` — reload page with selected period
- [x] Support 4th role color (System Admins) in `initRoleChart`

### 4. Testing

- [x] Verify analytics route returns 200 for each period value
- [x] Verify JSON payload reflects period filter
- [x] Verify no unresolved template vars
- [x] Verify JS syntax with node --check
