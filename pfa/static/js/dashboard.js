


document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll('.menu-item').forEach(item => {
        item.addEventListener('click', function () {
            // Remove 'active' class from all menu items
            document.querySelectorAll('.menu-item').forEach(i => i.classList.remove('active'));
            this.classList.add('active');

            // Hide all content sections
            document.querySelectorAll('.content-section').forEach(section => {
                section.classList.remove('active');
            });

            // Show the selected content section
            const target = this.getAttribute('data-target');
            document.getElementById(target).classList.add('active');
        });
    });
});

document.querySelector(".menu-toggle").addEventListener("click", function () {
    document.querySelector(".sidebar").classList.toggle("collapsed");
});


        // Switch between sections
        sidebarLinks.forEach(link => {
            link.addEventListener('click', function (event) {
                event.preventDefault();

                // Remove active class from all links and sections
                sidebarLinks.forEach(l => l.parentElement.classList.remove('active'));
                mainContents.forEach(content => content.classList.remove('active'));

                // Add active class to clicked link and corresponding section
                this.parentElement.classList.add('active');
                const targetId = this.getAttribute('data-content');
                const targetSection = document.getElementById(targetId);
                if (targetSection) {
                    targetSection.classList.add('active');
                }
            });
        });