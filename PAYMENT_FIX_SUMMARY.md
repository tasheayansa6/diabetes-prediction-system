# Payment Success Page Fix Summary

## Issues Fixed

### 1. **Auto-redirect was too slow (5 minutes → 5 seconds)**
   - **Before:** Countdown was 300 seconds (5 minutes)
   - **After:** Countdown is 5 seconds
   - **Impact:** Users are redirected to their dashboard immediately after payment confirmation

### 2. **Session expiration during Chapa redirect caused logout loop**
   - **Before:** `restoreSession()` only refreshed token if user object was missing
   - **After:** `restoreSession()` always checks token expiry and refreshes if <5 min remaining
   - **Impact:** Expired tokens are renewed before navigating to dashboard, preventing automatic logout

### 3. **Wrong user dashboard redirect after payment**
   - **Before:** Auto-redirect used service-specific URLs (e.g., `health_data_form.html`) which could trigger `checkAuth` failures
   - **After:** Auto-redirect always goes to role-based dashboard (`/templates/patient/dashboard.html`, `/templates/doctor/dashboard.html`, etc.)
   - **Impact:** Users always land on their correct dashboard regardless of role

### 4. **Countdown not visible immediately**
   - **Before:** Countdown appeared after first 1-second tick
   - **After:** Countdown shows immediately at "5s"
   - **Impact:** Better UX — users see the countdown right away

## Files Modified

1. **`frontend/static/js/payment-success.js`**
   - Added `_dashboardForCurrentUser()` helper for role-aware dashboard resolution
   - Rewrote `restoreSession()` to always check token expiry and refresh proactively
   - Changed auto-redirect from 300s → 5s
   - Auto-redirect now always goes to dashboard (not service-specific page)
   - Countdown shows immediately

2. **`frontend/templates/payment/payment_success.html`**
   - Removed duplicate `_refreshOnLoad()` inline script
   - Simplified `goToDashboard()` to use shared `restoreSession()` and `_dashboardForCurrentUser()`
   - Bumped cache-bust version to `?v=5`

## Testing Checklist

- [x] Chapa payment completes successfully
- [x] Auto-redirect happens after 5 seconds (not 5 minutes)
- [x] Countdown shows immediately at "5s"
- [x] User lands on correct role-based dashboard
- [x] Session is restored if token expired during Chapa redirect
- [x] No logout loop when navigating to dashboard
- [x] "Continue" button still works for service-specific navigation
- [x] "Dashboard" button works correctly
- [x] Works for all roles (patient, doctor, nurse, lab_technician, pharmacist, admin)

## How It Works Now

1. **Payment Success Page Loads**
   - `restoreSession()` runs immediately
   - Checks if token is expired or <5 min remaining
   - Refreshes token if needed

2. **Auto-Redirect (5 seconds)**
   - Countdown shows immediately: "Auto-redirecting to dashboard in 5s..."
   - After 5 seconds: `restoreSession()` runs again, then redirects to role-based dashboard

3. **Manual Navigation**
   - "Continue" button → goes to service-specific page (e.g., health form)
   - "Dashboard" button → goes to role-based dashboard
   - Both call `restoreSession()` before navigating

## Key Functions

### `_dashboardForCurrentUser(defaultTarget)`
Returns the correct dashboard URL based on user role:
- `patient` → `/templates/patient/dashboard.html`
- `doctor` → `/templates/doctor/dashboard.html`
- `nurse` → `/templates/nurse/dashboard.html`
- `lab_technician` → `/templates/lab/dashboard.html`
- `pharmacist` → `/templates/pharmacist/dashboard.html`
- `admin` → `/templates/admin/dashboard.html`
- Falls back to `defaultTarget` or patient dashboard if role unknown

### `restoreSession()`
Proactively refreshes JWT token:
1. Decodes current token
2. Checks expiry time
3. If <5 min remaining OR user object missing → calls `/api/auth/refresh`
4. Updates `localStorage` with new token and user object
5. Merges user data (never overwrites with null)

## Notes

- The "Continue" button still navigates to service-specific pages (e.g., health form for prediction payments)
- Auto-redirect always goes to dashboard for safety and consistency
- Token refresh happens silently in the background
- Works even if user session was lost during Chapa redirect (scans all `lastTransaction_*` keys)
