/* static/js/main.js */

/**
 * Menampilkan notifikasi toast.
 * @param {string} message Pesan yang akan ditampilkan.
 * @param {string} type Tipe toast ('success', 'error', 'warning', 'info').
 */
function showToast(message, type = 'info') {
    let colors;
    switch (type) {
        case 'success':
            colors = ['#10B981', '#34D399'];
            break;
        case 'error':
            colors = ['#EF4444', '#F87171'];
            break;
        case 'warning':
            colors = ['#F59E0B', '#FBBF24'];
            break;
        default:
            colors = ['#3B82F6', '#60A5FA'];
    }

    const toastNode = document.createElement("span");
    toastNode.textContent = message;

    const progressBar = document.createElement("div");
    progressBar.className = 'toastify-progress-bar';
    toastNode.appendChild(progressBar);

    Toastify({
        node: toastNode,
        duration: 5000,
        close: true,
        gravity: "bottom",
        position: "right",
        stopOnFocus: true,
        style: {
            background: `linear-gradient(to right, ${colors[0]}, ${colors[1]})`,
        },
        offset: {
            x: 20,
            y: 20
        },
        escapeMarkup: false
    }).showToast();
}

document.addEventListener('DOMContentLoaded', function() {
    // Logika untuk pengecekan tema awal dan event listener saklar tema
    // dipisahkan ke base.html (untuk load cepat) dan settings.html (khusus untuk halamannya)

    // Setup sidebar toggle hanya jika elemen sidebar ada
    if (document.querySelector('.sidebar')) {
        const sidebarToggle = document.getElementById('sidebar-toggle');
        const sidebarOverlay = document.querySelector('.sidebar-overlay');
        
        if (sidebarToggle) {
            sidebarToggle.addEventListener('click', function() {
                document.querySelector('.sidebar').classList.toggle('sidebar-show');
                sidebarOverlay.classList.toggle('active');
            });
        }
        
        if (sidebarOverlay) {
            sidebarOverlay.addEventListener('click', function() {
                document.querySelector('.sidebar').classList.remove('sidebar-show');
                sidebarOverlay.classList.remove('active');
            });
        }
    }
});