// Dark Mode Toggle
document.addEventListener('DOMContentLoaded', function() {
    // Initialize theme from localStorage
    const currentTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', currentTheme);
    updateThemeIcon(currentTheme);
    
    // Theme toggle click handler
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateThemeIcon(newTheme);
        });
    }
    
    function updateThemeIcon(theme) {
        const icon = document.querySelector('#themeToggle i');
        if (icon) {
            if (theme === 'dark') {
                icon.className = 'bi bi-sun-fill';
            } else {
                icon.className = 'bi bi-moon-stars-fill';
            }
        }
    }
});

// Animated Number Counter
function animateCounter(element, target, duration = 2000) {
    const start = 0;
    const increment = target / (duration / 16); // 60fps
    let current = start;
    
    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            element.textContent = target;
            clearInterval(timer);
        } else {
            element.textContent = Math.floor(current);
        }
    }, 16);
}

// Animate percentage counter
function animatePercentage(element, target, duration = 2000) {
    const start = 0;
    const increment = target / (duration / 16);
    let current = start;
    
    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            element.textContent = target + '%';
            clearInterval(timer);
        } else {
            element.textContent = Math.floor(current) + '%';
        }
    }, 16);
}

// Initialize counters on page load
document.addEventListener('DOMContentLoaded', function() {
    // Find all elements with data-counter attribute
    const counters = document.querySelectorAll('[data-counter]');
    
    counters.forEach(counter => {
        const target = parseInt(counter.getAttribute('data-counter'));
        const isPercentage = counter.textContent.includes('%');
        
        // Use Intersection Observer to trigger animation when visible
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    if (isPercentage) {
                        animatePercentage(counter, target, 1500);
                    } else {
                        animateCounter(counter, target, 1500);
                    }
                    observer.unobserve(counter);
                }
            });
        }, { threshold: 0.5 });
        
        observer.observe(counter);
    });
});

// Generate user initials for avatar
function getUserInitials(name) {
    if (!name) return '?';
    const parts = name.trim().split(' ');
    if (parts.length >= 2) {
        return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return parts[0].substring(0, 2).toUpperCase();
}

// Initialize avatars
document.addEventListener('DOMContentLoaded', function() {
    const avatars = document.querySelectorAll('[data-user-name]');
    avatars.forEach(avatar => {
        const userName = avatar.getAttribute('data-user-name');
        avatar.textContent = getUserInitials(userName);
    });
});
