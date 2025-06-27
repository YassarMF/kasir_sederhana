/* static/js/pos.js - VERSI FINAL DENGAN LOGIKA BARU */

// --- Variabel Global ---
const processTransactionUrl = window.posConfig.processTransactionUrl;
const username = window.posConfig.username;

let taxRatePercent = 0.0; // Nilai default, akan diupdate dari API
let taxRate = 0.0;        // Nilai default, akan diupdate dari API
let cart = [];
let lastTransactionData = null;

// --- Fungsi Utilitas ---
const formatRupiah = (amount) => `Rp ${new Intl.NumberFormat("id-ID").format(Math.round(amount))}`;
const showLoading = () => document.getElementById('loadingOverlay').style.display = 'flex';
const hideLoading = () => document.getElementById('loadingOverlay').style.display = 'none';
const escapeHtml = (text) => {
    const map = {'&':'&amp;', '<':'&lt ;', '>':'&gt;', '"':'&quot;', "'":'&#039;'};
    return String(text).replace(/[&<>"']/g, m => map[m]);
};

// --- Manajemen Local Storage ---
const saveCart = () => localStorage.setItem("pos_cart", JSON.stringify(cart));
const loadCart = () => {
    const savedCart = localStorage.getItem("pos_cart");
    cart = savedCart ? JSON.parse(savedCart) : [];
    updateCartDisplay();
};

// --- Fungsi Manajemen Keranjang ---
function addToCart(element) {
    const productItem = element.closest('.product-item');
    const id = parseInt(productItem.dataset.id);
    const name = productItem.dataset.name;
    const price = parseFloat(productItem.dataset.price);
    const stock = parseInt(productItem.dataset.stock);
    const existingItem = cart.find(item => item.id === id);
    if (existingItem) {
        if (existingItem.quantity < stock) {
            existingItem.quantity++;
        } else {
            showToast(`Stok ${name} tidak cukup.`, 'warning'); return;
        }
    } else {
        if (stock > 0) {
            cart.push({ id, name, price, quantity: 1, stock });
        } else {
            showToast(`Produk ${name} sedang kosong.`, 'warning'); return;
        }
    }
    showToast(`${name} ditambahkan ke keranjang`, 'success');
    updateCartDisplay();
}

function updateQuantity(id, change) {
    const itemIndex = cart.findIndex((item) => item.id === id);
    if (itemIndex > -1) {
        const item = cart[itemIndex];
        const newQuantity = item.quantity + change;
        if (newQuantity <= 0) {
            cart.splice(itemIndex, 1);
        } else if (newQuantity > item.stock) {
            showToast(`Stok ${item.name} tidak cukup.`, 'warning');
            return;
        } else {
            item.quantity = newQuantity;
        }
        updateCartDisplay();
    }
}

function removeItem(id) {
    cart = cart.filter((item) => item.id !== id);
    updateCartDisplay();
}

function clearCart() {
    if (cart.length > 0 && confirm("Anda yakin ingin mengosongkan keranjang?")) {
        cart = [];
        updateCartDisplay();
        showToast('Keranjang dikosongkan', 'info');
    }
}


// --- FUNGSI UPDATE TAMPILAN ---
function updateCartDisplay() {
    const cartItemsDiv = document.getElementById("cartItems");
    const emptyCartDiv = document.getElementById("emptyCart");
    const cartSummaryDiv = document.getElementById("cartSummary");
    const taxContainer = document.getElementById('tax-row-container');

    // Kosongkan kontainer pajak setiap kali fungsi ini dipanggil
    taxContainer.innerHTML = '';

    if (cart.length === 0) {
        cartItemsDiv.innerHTML = '';
        emptyCartDiv.classList.remove('d-none');
        cartSummaryDiv.style.display = "none";
    } else {
        emptyCartDiv.classList.add('d-none');
        cartSummaryDiv.style.display = "block";
        
        let cartHtml = '';
        let subtotal = 0;

        cart.forEach((item) => {
            const itemTotal = item.price * item.quantity;
            subtotal += itemTotal;
            cartHtml += `<div class="d-flex justify-content-between align-items-center py-2 border-bottom"><div class="flex-grow-1"><h6 class="mb-0 small">${escapeHtml(item.name)}</h6><small class="text-muted">${formatRupiah(item.price)}</small></div><div class="d-flex align-items-center ms-2"><button class="btn btn-sm btn-outline-secondary" onclick="updateQuantity(${item.id}, -1)">-</button><span class="mx-2 fw-bold">${item.quantity}</span><button class="btn btn-sm btn-outline-secondary" onclick="updateQuantity(${item.id}, 1)">+</button><button class="btn btn-sm text-danger ms-2" onclick="removeItem(${item.id})"><i class="fas fa-times"></i></button></div></div>`;
        });
        cartItemsDiv.innerHTML = cartHtml;

        const tax = subtotal * taxRate;
        const total = subtotal + tax;

        document.getElementById("subtotal").innerText = formatRupiah(subtotal);
        document.getElementById("total").innerText = formatRupiah(total);
        
        // Logika sesuai saran Anda: Hanya buat elemen jika pajak > 0
        if (taxRate > 0) {
            const taxRowHTML = `
                <div class="d-flex justify-content-between mb-2">
                    <span>Pajak (${taxRatePercent}%):</span> 
                    <span class="fw-bold">${formatRupiah(tax)}</span>
                </div>
            `;
            taxContainer.innerHTML = taxRowHTML;
        }
    }
    
    saveCart();
}

// --- Fungsi Transaksi & Struk ---
async function checkout() {
    if (cart.length === 0) { showToast("Keranjang belanja kosong!", 'warning'); return; }
    if (!confirm("Pastikan semua item sudah benar. Lanjutkan pembayaran?")) return;
    showLoading();
    try {
        const response = await fetch(processTransactionUrl, { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({ items: cart }), });
        const result = await response.json();
        if (!response.ok) throw new Error(result.message || 'Terjadi kesalahan server');
        cart = [];
        updateCartDisplay();
        showTransactionSuccess(result);
    } catch (error) {
        showToast(`Transaksi Gagal: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

function showTransactionSuccess(data) {
    lastTransactionData = data;
    document.getElementById('ts-id').value = `#${data.transaction_id}`;
    document.getElementById('ts-total').value = formatRupiah(data.total_amount);
    document.getElementById('ts-amount-paid').value = '';
    document.getElementById('ts-change').value = '';
    document.getElementById('print-receipt-btn').disabled = true;
    const successModal = new bootstrap.Modal(document.getElementById('transactionSuccessModal'));
    successModal.show();
}

function printReceipt() {
    if (!lastTransactionData) return;
    const amountPaid = parseFloat(document.getElementById('ts-amount-paid').value) || 0;
    const change = amountPaid - lastTransactionData.total_amount;
    const now = new Date();
    
    let taxHtml = '';
    if (taxRate > 0 && lastTransactionData.tax_amount > 0) {
        taxHtml = `<p style="display:flex; justify-content:space-between;"><span>Pajak (${taxRatePercent}%)</span> <span>${formatRupiah(lastTransactionData.tax_amount)}</span></p>`;
    }

    let receiptHtml = `<div style="font-family: 'Courier New', monospace; font-size: 12px; width: 280px; margin: 0 auto;"><p style="text-align:center; font-weight:bold; font-size: 14px;">KasirPro</p><p style="text-align:center; font-size: 10px; border-bottom: 1px dashed #333; padding-bottom: 5px;">Jl. Kode Program No. 101, Jakarta</p><p>ID Trans: #${lastTransactionData.transaction_id}<br>Kasir: ${username}<br>Tanggal: ${now.toLocaleDateString('id-ID')} ${now.toLocaleTimeString('id-ID')}</p><div style="border-top: 1px dashed #333; padding-top: 5px;">${(lastTransactionData.items || []).map(item => `<div>${escapeHtml(item.name)}</div><div style="display:flex; justify-content:space-between;"><span>${item.quantity}x ${formatRupiah(item.price)}</span><span>${formatRupiah(item.price * item.quantity)}</span></div>`).join('')}</div><div style="border-top: 1px dashed #333; margin-top: 5px; padding-top: 5px;"><p style="display:flex; justify-content:space-between;"><span>Subtotal</span> <span>${formatRupiah(lastTransactionData.subtotal)}</span></p>${taxHtml}<p style="display:flex; justify-content:space-between; font-weight:bold;"><span>TOTAL</span> <span>${formatRupiah(lastTransactionData.total_amount)}</span></p></div><div style="border-top: 1px dashed #333; margin-top: 5px; padding-top: 5px; font-weight:bold;"><p style="display:flex; justify-content:space-between;"><span>TUNAI</span> <span>${formatRupiah(amountPaid)}</span></p><p style="display:flex; justify-content:space-between;"><span>KEMBALI</span> <span>${formatRupiah(change)}</span></p></div><p style="text-align:center; margin-top: 15px; border-top: 1px dashed #333; padding-top: 5px;">Terima Kasih!</p></div>`;
    const pwin = window.open('', 'PRINT', 'height=600,width=400');
    pwin.document.write(`<html><head><title>Struk</title><style>body{font-family:"Courier New",monospace;font-size:12px;}div,p{margin:0;}</style></head><body>${receiptHtml}</body></html>`);
    pwin.document.close();
    pwin.focus();
    pwin.print();
    pwin.close();
}

function initializeSearch() {
    const searchInput = document.getElementById("searchProduct");
    searchInput.addEventListener("input", (e) => {
        const term = e.target.value.toLowerCase();
        document.querySelectorAll(".product-item").forEach(item => {
            const name = item.dataset.name.toLowerCase();
            const category = item.dataset.category.toLowerCase();
            if (name.includes(term) || category.includes(term)) {
                item.style.display = "";
            } else {
                item.style.display = "none";
            }
        });
    });
}

// --- Inisialisasi Utama ---
document.addEventListener("DOMContentLoaded", async () => {
    try {
        const response = await fetch('/api/get_settings');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const settings = await response.json();
        taxRatePercent = settings.tax_rate_percent;
        taxRate = taxRatePercent / 100.0;
        console.log(`Pajak berhasil diambil dari server: ${taxRatePercent}%`);
    } catch (error) {
        console.error('Gagal mengambil pengaturan pajak dari server:', error);
        showToast('Gagal memuat pengaturan pajak, menggunakan nilai default.', 'error');
    }

    loadCart();
    initializeSearch();
    
    const amountPaidInput = document.getElementById('ts-amount-paid');
    const changeOutput = document.getElementById('ts-change');
    const printBtn = document.getElementById('print-receipt-btn');
    
    amountPaidInput.addEventListener('input', function() {
        const amountPaid = parseFloat(this.value) || 0;
        if (lastTransactionData) {
            const total = lastTransactionData.total_amount;
            const change = amountPaid - total;
            changeOutput.value = formatRupiah(change);
            if (change >= 0) {
                changeOutput.style.color = 'var(--success-color)';
                printBtn.disabled = false;
            } else {
                changeOutput.style.color = 'var(--danger-color)';
                printBtn.disabled = true;
            }
        }
    });

    printBtn.addEventListener('click', printReceipt);
    
    const successModalEl = document.getElementById('transactionSuccessModal');
    successModalEl.addEventListener('hidden.bs.modal', function () {
        window.location.reload(); 
    });
});