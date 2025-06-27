/* static/js/product_search.js */

document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('productSearchInput');
    const tableBody = document.getElementById('productTableBody');
    const tableRows = tableBody.getElementsByTagName('tr');

    searchInput.addEventListener('keyup', function() {
        const searchTerm = searchInput.value.toLowerCase();

        for (let i = 0; i < tableRows.length; i++) {
            const row = tableRows[i];
            // Kolom ke-2 (index 1) adalah Nama Produk
            const nameCell = row.cells[1];
            // Kolom ke-5 (index 4) adalah Kategori
            const categoryCell = row.cells[4]; 
            
            if (nameCell && categoryCell) {
                const nameText = nameCell.textContent.toLowerCase();
                const categoryText = categoryCell.textContent.toLowerCase();

                // Tampilkan baris jika cocok dengan nama ATAU kategori
                if (nameText.includes(searchTerm) || categoryText.includes(searchTerm)) {
                    row.style.display = "";
                } else {
                    row.style.display = "none";
                }
            }
        }
    });
});