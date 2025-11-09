// DOM Elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const uploadBtn = document.getElementById('uploadBtn');
const cancelBtn = document.getElementById('cancelBtn');
const uploadControls = document.getElementById('uploadControls');
const uploadLoading = document.getElementById('uploadLoading');
const uploadStatus = document.getElementById('uploadStatus');
const inventoryContainer = document.getElementById('inventoryContainer');
const itemCount = document.getElementById('itemCount');
const clearBtn = document.getElementById('clearBtn');

let selectedFile = null;
let isUploading = false;

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
    const isTxt = file.type === 'text/plain' || file.name.endsWith('.txt');
    const isPdf = file.type === 'application/pdf' || file.name.endsWith('.pdf');

    if (!isTxt && !isPdf) {
        showStatus('Only .txt and .pdf files are allowed', 'error');
        return;
    }

    // Validate file size (10MB)
    if (file.size > 10 * 1024 * 1024) {
        showStatus('File is too large (max 10MB)', 'error');
        return;
    }

    selectedFile = file;
    uploadArea.style.display = 'none';
    uploadControls.style.display = 'block';

    const fileType = isTxt ? 'transcription' : 'receipt';
    const fileSize = (file.size / 1024).toFixed(1);
    showStatus(`✓ Selected: ${file.name} (${fileSize}KB) - Ready to upload as ${fileType}`, 'success');
}

// Upload button click
uploadBtn.addEventListener('click', uploadFile);
cancelBtn.addEventListener('click', cancelUpload);

async function uploadFile() {
    if (!selectedFile || isUploading) return;

    const formData = new FormData();
    formData.append('file', selectedFile);

    isUploading = true;
    uploadControls.style.display = 'none';
    uploadLoading.style.display = 'block';
    uploadStatus.style.display = 'none';

    try {
        const response = await fetch('/api/upload-transcription', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        uploadLoading.style.display = 'none';

        if (response.ok) {
            const itemCount = data.items.length;
            const message = `✓ Success! Added ${itemCount} item${itemCount !== 1 ? 's' : ''} to inventory from ${data.items[0].source}`;
            showStatus(message, 'success');

            // Show summary for 5 seconds then load inventory
            setTimeout(() => {
                selectedFile = null;
                uploadArea.style.display = 'block';
                uploadStatus.style.display = 'none';
                loadInventory();
            }, 2000);
        } else {
            showStatus(`✗ Error: ${data.error}`, 'error');
            uploadArea.style.display = 'block';
        }
    } catch (error) {
        console.error('Upload error:', error);
        uploadLoading.style.display = 'none';
        showStatus('✗ Error uploading file. Please try again.', 'error');
        uploadArea.style.display = 'block';
    } finally {
        isUploading = false;
    }
}

function cancelUpload() {
    selectedFile = null;
    uploadArea.style.display = 'block';
    uploadControls.style.display = 'none';
    uploadLoading.style.display = 'none';
    uploadStatus.style.display = 'none';
    fileInput.value = '';
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
        inventoryContainer.innerHTML = '<p class="empty-state">No items in inventory. Upload a transcription or receipt to get started!</p>';
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
    uploadStatus.style.display = 'block';

    if (type === 'success') {
        // Keep success messages visible for 5 seconds
        setTimeout(() => {
            uploadStatus.style.display = 'none';
        }, 5000);
    } else if (type === 'error') {
        // Keep error messages visible for 6 seconds
        setTimeout(() => {
            uploadStatus.style.display = 'none';
        }, 6000);
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
