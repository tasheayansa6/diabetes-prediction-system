// Login Page JavaScript (Connected to Flask Backend)

const API_BASE_URL = "";

// Handle login form submit
async function handleLogin(event) {
    event.preventDefault();

    // Get values
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;

    // Basic validation
    if (!email || !password) {
        alert("Please enter email and password");
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                email: email,
                password: password
            })
        });

        const data = await response.json();

        // ✅ SUCCESS
        if (response.ok && data.success) {
            console.log("Login success:", data);

            // Save token + user info
            localStorage.setItem("token", data.token);
            localStorage.setItem("user", JSON.stringify(data.user));

            // Redirect based on role
            redirectToDashboard(data.user.role);

        } else {
            // ❌ ERROR FROM BACKEND
            alert(data.message || "Login failed");
        }

    } catch (error) {
        console.error("Login error:", error);
        alert("Cannot connect to server. Make sure backend is running.");
    }
}

// Redirect user based on role
function redirectToDashboard(role) {
    const dashboards = {
        patient: "/templates/patient/dashboard.html",
        doctor: "/templates/doctor/dashboard.html",
        nurse: "/templates/nurse/dashboard.html",
        lab_technician: "/templates/lab/dashboard.html",
        pharmacist: "/templates/pharmacist/dashboard.html",
        admin: "/templates/admin/dashboard.html"
    };

    const redirectUrl = dashboards[role];

    if (redirectUrl) {
        window.location.href = redirectUrl;
    } else {
        alert("Unknown role: " + role);
    }
}

// Check if already logged in (validate token expiry)
window.addEventListener("DOMContentLoaded", function () {
    const token = localStorage.getItem("token");
    const user = JSON.parse(localStorage.getItem("user") || '{}');
    if (!token || !user.role) return;
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        if (payload.exp && payload.exp * 1000 > Date.now()) {
            redirectToDashboard(user.role);
        } else {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
        }
    } catch { localStorage.removeItem('token'); localStorage.removeItem('user'); }
});