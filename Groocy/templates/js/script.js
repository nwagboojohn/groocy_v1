// --- 1. Cart Management ---
let cart = JSON.parse(localStorage.getItem('groocyCart')) || [];

// calls toast notification when user adds item to cart
function showToast(message) {
    const toast = document.getElementById('toast');
    toast.innerText = message;
    toast.classList.add('show');

    // Hide it after 2 seconds
    setTimeout(() => {
        toast.classList.remove('show');
    }, 2000);
}

// Added 'image' parameter
function addToCart(id, name, price, image) {
    // 1. Find the specific card and stock element
    const card = document.querySelector(`.card[data-name="${name.toLowerCase()}"]`);
    const stockElement = card ? card.querySelector('.quantity') : null;

    // Validation: If the UI element is missing, we can't check stock safely
    if (!stockElement) {
        console.error("Could not find stock element for", name);
        return;
    }

    // 2. Parse current available stock
    const availableStock = parseInt(stockElement.innerText);

    // 3. Find if the item is already in the cart
    const existingItem = cart.find(item => item.id === id);
    const currentQtyInCart = existingItem ? existingItem.quantity : 0;

    // 4. Stock Validation
    if (availableStock <= 0) {
        alert(`Sorry, ${name} is currently out of stock!`);
        return;
    }

    if (currentQtyInCart >= availableStock) {
        alert(`Sorry, we only have ${availableStock} units of ${name} left!`);
        return;
    }

    // 5. Add or Increment (Logic is perfect here)
    if (existingItem) {
        existingItem.quantity += 1; 
    } else {
        // Ensure price is a number; remove any commas or currency symbols if they exist
        const cleanPrice = typeof price === 'string' ? parseFloat(price.replace(/[^0-9.]/g, '')) : price;
        cart.push({ id, name, price: cleanPrice, image, quantity: 1 });
    }

    // 6. Save and Sync
    localStorage.setItem('groocyCart', JSON.stringify(cart));
    updateCartUI();
    showToast(`${name} added to bag! 🛒`);
}

async function syncCartToSession() {
    try {
        await fetch('/sync-cart/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'), 
            },
            body: JSON.stringify({ cart: cart })
        });
    } catch (error) {
        console.error("Cart sync failed:", error);
    }
}

// Helper to get CSRF token from cookies
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function updateCartUI() {
    const container = document.getElementById('cartItems');
    const subtotalSpan = document.getElementById('subtotalPrice');
    const shippingSpan = document.getElementById('shippingFee');
    const totalSpan = document.getElementById('totalPrice');
    
    // 1. Calculate the Subtotal and check if order is less than MIN_ORDER_AMOUNT
    let subtotal = cart.reduce((sum, item) => sum + parseFloat(item.price * item.quantity), 0);
    const checkoutBtn = document.getElementById('payButton');
    const minOrderMsg = document.getElementById('minOrderWarning'); // Add this ID in your HTML
    const minOrderText = document.getElementById('minOrderText');

    if (subtotal > 0 && subtotal < 1000) {
        let remaining = 1000 - subtotal;
        minOrderText.innerText = `Add ₦${remaining.toLocaleString()} more to checkout`;
        minOrderMsg.style.display = "block";

        // Visual cue: make button look disabled
        checkoutBtn.style.opacity = "0.5";
        checkoutBtn.style.cursor = "not-allowed"
    } else {
        minOrderMsg.style.display = "none";
        checkoutBtn.style.opacity = "1";
        checkoutBtn.style.cursor = "pointer"
    }
    
    // 2. Add Shipping only if there are items in the cart
    let shippingFee = subtotal > 0 ? 100 : 0;

    // 3. Calculate Grand Total
    let total = subtotal + shippingFee;

    // Render Cart Items
    container.innerHTML = cart.map((item, index) => `
        <div class="cart-item" style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 15px;">
            <img src="${item.image}" class="cart-img" style="width: 50px; height: 50px; border-radius: 8px;">
            <div class="cart-item-info" style="flex: 1; margin-left: 5px;">
                <p style="margin: 0; font-weight: 600;">${item.name}</p>
                <span style="font-size: 0.8rem; color: #666;">₦${item.price.toLocaleString()} x ${item.quantity}</span>
            </div>
            <div class="qty-controls" style="display: flex; align-items: center; gap: 8px;">
                <button onclick="changeQty(${index}, -1)" style="border:none; background:#eee; border-radius:4px; width:24px; cursor: pointer;">-</button>
                <span>${item.quantity}</span>
                <button onclick="changeQty(${index}, 1)" style="border:none; background:#eee; border-radius:4px; width:24px; cursor: pointer;">+</button>
            </div>
        </div>
    `).join('');

    // Calculate total items for badge
    const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);

    // 1. Handle Top Header Badge
    const headerBadge = document.getElementById('cartCountBadge');
    if (headerBadge) {
        headerBadge.innerText = totalItems;
        // Only show if items > 0 AND it's not hidden by CSS
        headerBadge.style.display = (totalItems > 0) ? "block" : "none";
    }

    // 2. Handle Bottom Nav Badge
    const mobileBadge = document.getElementById('mobileCartBadge');
    if (mobileBadge) {
        mobileBadge.innerText = totalItems;
        // Only show if items > 0
        mobileBadge.style.display = (totalItems > 0) ? "block" : "none";
    }

    // 4. Update the Total Display
    subtotalSpan.innerText = subtotal.toLocaleString(undefined, {minimumFractionDigits: 2});
    shippingSpan.innerText = shippingFee.toLocaleString(undefined, {minimumFractionDigits: 2});
    totalSpan.innerText = total.toLocaleString(undefined, {minimumFractionDigits: 2});
}

// added an "Out of Stock" label to products when their instock hits zero '0'
function checkStockLevels() {
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        const qtySpan = card.querySelector('.quantity');
        const btn = card.querySelector('button');
        const stock = parseInt(qtySpan.innerText);

        if (stock <= 0) {
            btn.innerText = "Out of Stock";
            btn.classList.add('out-of-stock-btn');
            btn.onclick = null; // Remove the click function
            qtySpan.classList.add('out-of-stock-label');
        }
    });
}

// New helper function to handle + and - in cart
function changeQty(index, delta) {
    cart[index].quantity += delta;
    if (cart[index].quantity <= 0) {
        cart.splice(index, 1); // Remove if quantity hits 0
    }
    localStorage.setItem('groocyCart', JSON.stringify(cart));
    updateCartUI();
}

function removeFromCart(index) {
    cart.splice(index, 1);
    localStorage.setItem('groocyCart', JSON.stringify(cart));
    updateCartUI();
}

// // Toggle Sidebar (Mobile)
// function toggleSidebar() {
//     const sidebar = document.getElementById('sidebar');
//     const overlay = document.getElementById('drawerOverlay'); // Re-using your overlay

//     sidebar.classList.toggle('active');
//     overlay.classList.toggle('active');

//     // Manage scroll
//     document.body.style.overflow = sidebar.classList.contains('active') ? 'hidden' : 'auto';
// }

// --- Drawer Toggle Helper ---
function toggleCartDrawer() {
    const drawer = document.getElementById('cartDrawer');
    const overlay = document.getElementById('drawerOverlay');

    // Toggle the 'active' class on both
    drawer.classList.toggle('active');
    overlay.classList.toggle('active');

    // Prevent scrolling on the main page when cart is open
    if (drawer.classList.contains('active')) {
        document.body.style.overflow = 'hidden';
    } else {
        document.body.style.overflow = 'auto';
    }
}

// make sure the drawerOverlay click function handles whatever is open
// function closeEverything() {
//     document.getElementById('sidebar').classList.remove('active');
//     document.getElementById('cartDrawer').classList.remove('active');
//     document.getElementById('drawerOverlay').classList.remove('active');
//     document.body.style.overflow = 'auto';
// }


// --- 2. Search Logic ---
function liveSearch() {
    let input = document.getElementById('searchInput').value.toLowerCase();
    let cards = document.querySelectorAll('.card');
    let visibleCount = 0;

    cards.forEach(card => {
        if (card.getAttribute('data-name').includes(input)) {
            card.style.display = "block";
            visibleCount++;
        } else {
            card.style.display = "none";
        }
    });

    document.getElementById('productGrid').style.display = visibleCount ? "grid" : "none";
    document.getElementById('noResult').style.display = visibleCount ? "none" : "block";
}

// --- 3. Address Function
function openAddressModal() {
    document.getElementById('addressModal').style.display = 'flex';
}

function closeAddressModal() {
    document.getElementById('addressModal').style.display = 'none';
}

function saveAddress() {
    const addr = document.getElementById('addressInput').value;
    if(addr) {
        localStorage.setItem('groocyAddress', addr);
        document.getElementById('displayAddress').innerText = addr;
        closeAddressModal();
    }
}

// Load address on page load
window.addEventListener('load', () => {
    const savedAddr = localStorage.getItem('groocyAddress');
    if(savedAddr) {
        document.getElementById('displayAddress').innerText = savedAddr;
        document.getElementById('addressInput').value = savedAddr;
    }
});


// --- 4. Filter Category ---
function filterCategory(category, button) {
    let cards = document.querySelectorAll('.card');
    let productGrid = document.getElementById('productGrid');
    let noResult = document.getElementById('noResult');
    let visibleCount = 0;

    // 1. Update UI: Remove 'active' class from all buttons and add to the clicked one
    document.querySelectorAll('.category-option').forEach(btn => btn.classList.remove('active'));
    button.classList.add('active');

    // 2. Filter Logic
    cards.forEach(card => {
        let productCat = card.getAttribute('data-category');
        
        if (category === 'all' || productCat === category) {
            card.style.display = "block";
            visibleCount++;
        } else {
            card.style.display = "none";
        }
    });

    // 3. Handle Empty State
    if (visibleCount === 0) {
        productGrid.style.display = "none";
        noResult.style.display = "block";
    } else {
        productGrid.style.display = "grid";
        noResult.style.display = "none";
    }
}


// --- 5. Paystack Integration ---
async function payWithPaystack() {
    const btnText = document.getElementById('btnText');
    const btnSpinner = document.getElementById('btnSpinner');
    const payBtn = document.getElementById('payButton');

    // 1. Calculate subtotal once using parseFloat
    let subtotal = cart.reduce((sum, item) => sum + parseFloat(item.price * item.quantity), 0);
    const MIN_ORDER_AMOUNT = 1000; // Set your limit here

    // 2. Check if the subtotal meets the minimum requirement
    if (subtotal < MIN_ORDER_AMOUNT) {
        // We use a friendly alert, or you could show a red error message on the page
        alert(`🛒 Your cart total is ₦${subtotal}. Please you can't purchase items less than ₦${MIN_ORDER_AMOUNT}.`);
        return;
    }

    // 3. Single check for empty cart
    if (subtotal <= 0){
        return alert("Your cart is empty!")
    }

    // 4. Define the shipping fee
    const shippingfee = 100;

    // Show loading State
    btnText.innerHTML = "Processing...";
    btnSpinner.style.display = "inline-block";
    payBtn.disabled = true; // Prevent multiple clicks

    // 5. Calculate total and convert to Kobo
    let totalInKobo = Math.round((subtotal + shippingfee) * 100)

    // SYNC DATA TO DJANGO SESSION FIRST
    await syncCartToSession();

    let handler = PaystackPop.setup({
        key: '{{ paystack_public_key }}',
        email: '{{ user.email }}',
        amount: totalInKobo,
        currency: 'NGN',
        onClose: function() {
            // Reset button if they close the window without paying
            btnText.innerText = "Checkout";
            btnSpinner.style.display = "none";
            payBtn.disabled = false;
        },
        callback: function(response) {
            btnText.innerHTML = "Redirecting..."
            window.location.href = "/verify-payment/" + response.reference;
            localStorage.removeItem('groocyCart'); // Clear cart on success
        }
    });
    handler.openIframe();
}

// Initialize UI when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize UI
    updateCartUI();
    // Call this function whenever the page loads
    checkStockLevels();
    
    // Load saved address
    const savedAddr = localStorage.getItem('groocyAddress');
    if(savedAddr) {
        document.getElementById('displayAddress').innerText = savedAddr;
        const addrInput = document.getElementById('addressInput');
        if(addrInput) addrInput.value = savedAddr;
    }
});
