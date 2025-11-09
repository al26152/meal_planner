// DOM Elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const uploadBtn = document.getElementById('uploadBtn');
const uploadStatus = document.getElementById('uploadStatus');
const inventoryContainer = document.getElementById('inventoryContainer');
const itemCount = document.getElementById('itemCount');
const clearBtn = document.getElementById('clearBtn');

let selectedFile = null;

// ===== Upload Handling =====

// Click to select file
uploadArea.addEventListener('click', () => fileInput.click());

// File input change
fileInput.addEventListener('change', (e) => {
    handleFileSelect(e.target.files[0]);
});

// Drag and drop
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    handleFileSelect(e.dataTransfer.files[0]);
});

function handleFileSelect(file) {
    if (!file) return;

    // Validate file type
    if (file.type !== 'text/plain' && !file.name.endsWith('.txt')) {
        showStatus('Only .txt files are allowed', 'error');
        return;
    }

    // Validate file size (5MB)
    if (file.size > 5 * 1024 * 1024) {
        showStatus('File is too large (max 5MB)', 'error');
        return;
    }

    selectedFile = file;
    uploadArea.style.display = 'none';
    uploadBtn.style.display = 'block';
    showStatus(`Selected: ${file.name}`, 'success');
}

// Upload button click
uploadBtn.addEventListener('click', uploadFile);

async function uploadFile() {
    if (!selectedFile) return;

    const formData = new FormData();
    formData.append('file', selectedFile);

    showStatus('Uploading and processing...', 'loading');
    uploadBtn.disabled = true;

    try {
        const response = await fetch('/api/upload-transcription', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            showStatus(`✓ ${data.message}`, 'success');
            selectedFile = null;
            uploadBtn.style.display = 'none';
            uploadArea.style.display = 'block';
            loadInventory();
        } else {
            showStatus(`Error: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Upload error:', error);
        showStatus('Error uploading file', 'error');
    } finally {
        uploadBtn.disabled = false;
    }
}

// ===== Inventory Display =====

async function loadInventory() {
    try {
        const response = await fetch('/api/inventory');
        const data = await response.json();

        if (data.success) {
            displayInventory(data.items);
            updateItemCount(data.count);
        }
    } catch (error) {
        console.error('Error loading inventory:', error);
    }
}

function displayInventory(items) {
    if (items.length === 0) {
        inventoryContainer.innerHTML = '<p class="empty-state">No items in inventory. Upload a transcription to get started!</p>';
        return;
    }

    // Group items by category
    const grouped = {};
    items.forEach(item => {
        const category = item.category || 'other';
        if (!grouped[category]) {
            grouped[category] = [];
        }
        grouped[category].push(item);
    });

    let html = '';

    // Sort categories alphabetically
    Object.keys(grouped).sort().forEach(category => {
        grouped[category].forEach(item => {
            html += createInventoryItemHTML(item);
        });
    });

    inventoryContainer.innerHTML = html;

    // Add delete event listeners
    document.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            deleteItem(btn.dataset.itemId);
        });
    });
}

function createInventoryItemHTML(item) {
    const addedDate = new Date(item.added_date).toLocaleDateString();

    return `
        <div class="inventory-item">
            <button class="delete-btn" data-item-id="${item.id}" title="Delete item">×</button>
            <div class="item-name">${escapeHTML(item.name)}</div>
            <div class="item-details">
                <div class="item-detail">
                    <span class="detail-label">Quantity</span>
                    <span class="detail-value">${item.quantity} ${item.unit}</span>
                </div>
                <div class="item-detail">
                    <span class="detail-label">Category</span>
                    <span class="detail-value">${escapeHTML(item.category)}</span>
                </div>
            </div>
            <div class="item-metadata">
                <span class="item-source">${item.source}</span>
                <span title="${item.added_date}">${addedDate}</span>
            </div>
        </div>
    `;
}

function updateItemCount(count) {
    itemCount.textContent = `${count} item${count !== 1 ? 's' : ''}`;
}

// ===== Item Management =====

async function deleteItem(itemId) {
    if (!confirm('Are you sure you want to delete this item?')) {
        return;
    }

    try {
        const response = await fetch(`/api/inventory/${itemId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (response.ok) {
            loadInventory();
        } else {
            console.error('Error deleting item:', data.error);
        }
    } catch (error) {
        console.error('Delete error:', error);
    }
}

// Clear all inventory
clearBtn.addEventListener('click', async () => {
    if (!confirm('Are you sure you want to clear all items? This cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch('/api/inventory', {
            method: 'DELETE'
        });

        const data = await response.json();

        if (response.ok) {
            loadInventory();
            showStatus('Inventory cleared', 'success');
        } else {
            showStatus(`Error: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Clear error:', error);
        showStatus('Error clearing inventory', 'error');
    }
});

// ===== Utility Functions =====

function showStatus(message, type) {
    uploadStatus.textContent = message;
    uploadStatus.className = `status-message ${type}`;

    if (type !== 'loading') {
        setTimeout(() => {
            uploadStatus.className = 'status-message';
            uploadStatus.textContent = '';
        }, 5000);
    }
}

function escapeHTML(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ===== Initialize =====

// Load inventory on page load
document.addEventListener('DOMContentLoaded', () => {
    loadInventory();

    // Refresh inventory every 30 seconds
    setInterval(loadInventory, 30000);
});
