(function () {
    function refreshRequests() {
        const requests = document.querySelector("[data-requests-url]");
        if (requests === null) {
            return;
        }
        htmx.ajax("GET", requests.dataset.requestsUrl, {
            target: "#requests",
            swap: "outerHTML",
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        window.setInterval(refreshRequests, 5000);
    });
})();