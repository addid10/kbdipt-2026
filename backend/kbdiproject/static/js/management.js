(() => {
    const sidebar = document.querySelector("#management-sidebar");
    const toggle = document.querySelector("[data-sidebar-toggle]");
    const backdrop = document.querySelector("[data-sidebar-backdrop]");
    if (!sidebar || !toggle || !backdrop) return;

    const close = () => {
        sidebar.classList.remove("open");
        backdrop.classList.remove("show");
    };
    toggle.addEventListener("click", () => {
        sidebar.classList.toggle("open");
        backdrop.classList.toggle("show");
    });
    backdrop.addEventListener("click", close);
})();
