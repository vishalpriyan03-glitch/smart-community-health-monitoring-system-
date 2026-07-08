document.addEventListener('DOMContentLoaded', () => {
    // Auto-dismiss flash messages after 5 seconds
    document.querySelectorAll('.flash').forEach((flash) => {
        setTimeout(() => {
            flash.style.transition = 'opacity 0.4s ease';
            flash.style.opacity = '0';
            setTimeout(() => flash.remove(), 400);
        }, 5000);
    });
});
