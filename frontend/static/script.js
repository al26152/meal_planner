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

    // Add edit event listeners
    document.querySelectorAll('.edit-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            editItem(btn.dataset.itemId);
        });
    });

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
            <div class="item-actions">
                <button class="edit-btn" data-item-id="${item.id}" title="Edit item">✎</button>
                <button class="delete-btn" data-item-id="${item.id}" title="Delete item">×</button>
            </div>
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

async function editItem(itemId) {
    // Find the item in the DOM
    const items = document.querySelectorAll('.inventory-item');
    let itemData = null;

    // Get current item data by parsing the DOM (simple approach)
    // For a better solution, we'd store this in the HTML data attributes
    for (let item of items) {
        const editBtn = item.querySelector(`[data-item-id="${itemId}"]`);
        if (editBtn) {
            // Extract data from displayed item
            const name = item.querySelector('.item-name').textContent;
            const quantityText = item.querySelector('.item-details .item-detail:nth-child(1) .detail-value').textContent;
            const [quantity, unit] = quantityText.split(' ');
            const category = item.querySelector('.item-details .item-detail:nth-child(2) .detail-value').textContent;
            const notes = ''; // Add notes from data attribute if available

            itemData = { id: itemId, name, quantity, unit, category, notes };
            break;
        }
    }

    if (!itemData) return;

    // Create modal
    const modal = document.createElement('div');
    modal.className = 'edit-modal';
    modal.innerHTML = `
        <div class="edit-modal-content">
            <h3>Edit Item</h3>
            <form id="editForm">
                <div class="form-group">
                    <label>Item Name</label>
                    <input type="text" id="editName" value="${escapeHTML(itemData.name)}" required>
                </div>
                <div class="form-group">
                    <label>Quantity</label>
                    <input type="number" id="editQuantity" value="${itemData.quantity}" step="0.1" required>
                </div>
                <div class="form-group">
                    <label>Unit</label>
                    <input type="text" id="editUnit" value="${escapeHTML(itemData.unit)}" required>
                </div>
                <div class="form-group">
                    <label>Category</label>
                    <select id="editCategory" required>
                        <option value="dairy" ${itemData.category === 'dairy' ? 'selected' : ''}>Dairy</option>
                        <option value="meat" ${itemData.category === 'meat' ? 'selected' : ''}>Meat</option>
                        <option value="produce" ${itemData.category === 'produce' ? 'selected' : ''}>Produce</option>
                        <option value="pantry" ${itemData.category === 'pantry' ? 'selected' : ''}>Pantry</option>
                        <option value="bakery" ${itemData.category === 'bakery' ? 'selected' : ''}>Bakery</option>
                        <option value="snacks" ${itemData.category === 'snacks' ? 'selected' : ''}>Snacks</option>
                        <option value="beverages" ${itemData.category === 'beverages' ? 'selected' : ''}>Beverages</option>
                        <option value="frozen" ${itemData.category === 'frozen' ? 'selected' : ''}>Frozen</option>
                        <option value="other" ${itemData.category === 'other' ? 'selected' : ''}>Other</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Notes</label>
                    <textarea id="editNotes" placeholder="Add notes about this item" style="width: 100%; min-height: 60px;">${escapeHTML(itemData.notes)}</textarea>
                </div>
                <div class="form-actions">
                    <button type="submit" class="btn btn-primary">Save Changes</button>
                    <button type="button" class="btn btn-secondary" onclick="this.closest('.edit-modal').remove()">Cancel</button>
                </div>
            </form>
        </div>
    `;

    document.body.appendChild(modal);

    // Handle form submission
    document.getElementById('editForm').addEventListener('submit', async (e) => {
        e.preventDefault();

        const name = document.getElementById('editName').value;
        const quantity = parseFloat(document.getElementById('editQuantity').value);
        const unit = document.getElementById('editUnit').value;
        const category = document.getElementById('editCategory').value;
        const notes = document.getElementById('editNotes').value;

        try {
            const response = await fetch(`/api/inventory/${itemId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name,
                    quantity,
                    unit,
                    category,
                    notes
                })
            });

            const data = await response.json();

            if (response.ok) {
                modal.remove();
                loadInventory();
                showStatus('✓ Item updated successfully', 'success');
            } else {
                showStatus(`✗ Error: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('Edit error:', error);
            showStatus('✗ Error updating item', 'error');
        }
    });

    // Close modal on outside click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    });
}

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
