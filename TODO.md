# MediChain — System Admin Manage Hospitals Page

## Completed Tasks

### 1. Database Integration

- ✅ `system_admin_hospitals()` route fetches ALL hospitals from `hospitals` table
- ✅ Stats: active, pending, suspended, rejected counts from DB
- ✅ Doctor count per hospital via `users` table (role='doctor')
- ✅ All fields populated from DB (no hardcoded data)

### 2. Flask API Endpoints (JSON)

- ✅ `GET /system-admin/api/hospitals` — full hospital list for JS
- ✅ `POST /system-admin/hospitals/update` — update hospital info
- ✅ `POST /system-admin/hospitals/<id>/status` — approve/reject/suspend/activate
- ✅ `POST /system-admin/hospitals/<id>/delete` — delete hospital + linked users

### 3. Frontend — Template (hospitals.html)

- ✅ `{{ hospitals|tojson }}` data cache via `#hospitals-data` script tag
- ✅ Table rows have `data-hospital-id` + `data-status` attributes
- ✅ Modal with editable fields: name, registration, city, status, address, phone, email
- ✅ Status filter now includes "Rejected" option
- ✅ Action buttons rendered based on status (pending → approve/reject, suspended → activate, else → suspend)
- ✅ View/Edit/Delete buttons present for all hospitals
- ✅ Pagination + table sort preserved

### 4. Frontend — JavaScript (system-admin.js)

- ✅ `MediChainHospitals` module with IIFE pattern
- ✅ `bindActions()` — attaches click handlers to all action buttons
- ✅ `openModal(id, mode)` — view/edit mode with proper field disabling
- ✅ `saveHospitalChanges()` — validates, POSTs update, refreshes row + counts
- ✅ `changeStatus(id, status)` — SweetAlert confirm → fetch → UI refresh
- ✅ `deleteHospital(id)` — SweetAlert confirm → fetch → row removal + recount
- ✅ `refreshCounts()` — dynamically updates all stat cards, header badge, footer, sidebar badge
- ✅ `updateRow()` — refreshes individual table row (name, reg, city, status badge, actions)
- ✅ `renderActions()` — re-renders action buttons based on new status

### 5. Status: Pending

- Approve/Reject buttons shown
- Activate button shown for Suspended
- Suspend button shown for Approved/Rejected

## Still To Do

- ⬜ Wire "Export CSV" button to download data
- ⬜ Any additional testing
