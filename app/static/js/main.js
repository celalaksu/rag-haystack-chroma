// Basic JavaScript for Flask application
document.addEventListener('DOMContentLoaded', function() {
    console.log('Flask application with Jinja templates loaded successfully!');
    
    // Add a simple animation to the features list
    const featureItems = document.querySelectorAll('.card ul li');
    if (featureItems.length > 0) {
        featureItems.forEach((item, index) => {
            setTimeout(() => {
                item.style.opacity = '1';
            }, index * 200);
        });
    }
});