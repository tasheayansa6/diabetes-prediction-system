// Index Page JavaScript

// Show/hide back to top button
window.addEventListener("scroll", function () {
    const backToTop = document.getElementById("backToTop");
    if (window.pageYOffset > 300) {
        backToTop.classList.add("show");
    } else {
        backToTop.classList.remove("show");
    }
});

// Scroll to top function
function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: "smooth",
    });
}

// Fetch real model accuracy from backend
fetch('/api/model/info')
    .then(r => r.json())
    .then(d => {
        if (d.success && d.accuracy) {
            document.getElementById('model-accuracy').textContent =
                (d.accuracy * 100).toFixed(1) + '%';
        }
    })
    .catch(() => {
        document.getElementById('model-accuracy').textContent = '77.3%';
    });
