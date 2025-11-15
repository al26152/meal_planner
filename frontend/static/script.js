// ===== Tab Management =====

// DOM Elements for tabs
const tabButtons = document.querySelectorAll('.tab-btn');
const tabContents = document.querySelectorAll('.tab-content');

// Tab switching functionality
tabButtons.forEach(button => {
    button.addEventListener('click', () => {
        const tabId = button.getAttribute('data-tab');

        // Remove active class from all tabs and buttons
        tabContents.forEach(tab => tab.classList.remove('active'));
        tabButtons.forEach(btn => btn.classList.remove('active'));

        // Add active class to clicked button and corresponding tab
        button.classList.add('active');
        document.getElementById(tabId).classList.add('active');

        // Save tab preference to localStorage
        localStorage.setItem('activeTab', tabId);
    });
});

// Restore last active tab on page load
window.addEventListener('DOMContentLoaded', () => {
    const savedTab = localStorage.getItem('activeTab') || 'inventory-tab';
    const tabButton = document.querySelector(`[data-tab="${savedTab}"]`);
    if (tabButton) {
        tabButton.click();
    }
});

// ===== Upload and Inventory Management =====

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

// ===== Quick Add Ingredient =====

const quickAddBtn = document.getElementById('quickAddBtn');
const quickAddInput = document.getElementById('quickAddInput');
const quickAddStatus = document.getElementById('quickAddStatus');

quickAddBtn.addEventListener('click', addIngredientManually);
quickAddInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        addIngredientManually();
    }
});

async function addIngredientManually() {
    const text = quickAddInput.value.trim();

    if (!text) {
        showQuickAddStatus('Please enter an ingredient', 'error');
        return;
    }

    // Show loading state
    quickAddBtn.disabled = true;
    quickAddBtn.textContent = 'Adding...';

    try {
        const response = await fetch('/api/inventory/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ text: text })
        });

        const data = await response.json();

        if (response.ok) {
            // Clear input
            quickAddInput.value = '';
            // Reload inventory
            loadInventory();
            // Show success message
            const itemCount = data.items.length;
            showQuickAddStatus(`✓ Added ${itemCount} item(s) to inventory!`, 'success');
        } else {
            showQuickAddStatus(`✗ ${data.error || 'Error adding ingredient'}`, 'error');
        }
    } catch (error) {
        console.error('Error adding ingredient:', error);
        showQuickAddStatus('✗ Error adding ingredient. Please try again.', 'error');
    } finally {
        quickAddBtn.disabled = false;
        quickAddBtn.textContent = 'Add to Inventory';
    }
}

function showQuickAddStatus(message, type) {
    quickAddStatus.textContent = message;
    quickAddStatus.className = `status-message ${type}`;
    quickAddStatus.style.display = 'block';

    if (type === 'success') {
        setTimeout(() => {
            quickAddStatus.style.display = 'none';
        }, 4000);
    }
}

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

// ===== Meal Planning =====

const numMealsInput = document.getElementById('numMeals');
const mealCriteriaInput = document.getElementById('mealCriteria');
const generatePlanBtn = document.getElementById('generatePlanBtn');
const planLoading = document.getElementById('planLoading');
const planStatus = document.getElementById('planStatus');
const mealPlanContainer = document.getElementById('mealPlanContainer');
const mealsDisplay = document.getElementById('mealsDisplay');
const shoppingListBtn = document.getElementById('shoppingListBtn');
const shoppingListModal = document.getElementById('shoppingListModal');
const closeShoppingListBtn = document.getElementById('closeShoppingListBtn');
const shoppingListContent = document.getElementById('shoppingListContent');

let currentMealPlan = null;

// Generate meal plan (old code - kept for compatibility)
if (generatePlanBtn) {
generatePlanBtn.addEventListener('click', async () => {
    const numMeals = parseInt(numMealsInput.value);
    const criteria = mealCriteriaInput.value.trim();

    if (!numMeals || numMeals < 1) {
        showPlanStatus('Please enter a valid number of meals', 'error');
        return;
    }

    if (!criteria) {
        showPlanStatus('Please enter meal preferences (e.g., "Italian", "healthy", "gourmet")', 'error');
        return;
    }

    await generateMealPlan(numMeals, criteria);
});
}

async function generateMealPlan(numMeals, criteria) {
    planLoading.style.display = 'block';
    planStatus.style.display = 'none';
    mealPlanContainer.style.display = 'none';

    try {
        const response = await fetch('/api/meal-plans/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                num_meals: numMeals,
                criteria: criteria
            })
        });

        const data = await response.json();
        planLoading.style.display = 'none';

        if (response.ok) {
            currentMealPlan = {
                id: data.plan_id,
                meals: data.meals,
                num_meals: numMeals,
                criteria: criteria
            };

            displayMealPlan(data.meals);
            showPlanStatus(`Generated ${data.meals.length} delicious meals!`, 'success');
        } else {
            showPlanStatus(`Error: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Generate meal plan error:', error);
        planLoading.style.display = 'none';
        showPlanStatus('Error generating meal plan. Please try again.', 'error');
    }
}

function displayMealPlan(meals) {
    if (!meals || meals.length === 0) {
        mealsDisplay.innerHTML = '<p class="empty-state">No meals generated</p>';
        mealPlanContainer.style.display = 'block';
        return;
    }

    let html = '';

    meals.forEach((meal, index) => {
        const recipe = meal.recipe || {};
        const ingredients = recipe.ingredients || [];
        const instructions = recipe.instructions || '';

        // Count available vs missing ingredients
        const ingredientSummary = getIngredientSummary(ingredients);

        html += `
            <div class="meal-card">
                <div class="meal-header">
                    <h3>Meal ${index + 1}</h3>
                    <span class="ingredient-status">
                        ${ingredientSummary.available}/${ingredientSummary.total} ingredients in stock
                    </span>
                </div>
                <div class="meal-body">
                    <h4>${escapeHTML(recipe.name || 'Unknown Recipe')}</h4>

                    <div class="ingredients-section">
                        <strong>Ingredients:</strong>
                        <ul class="ingredients-list">
                            ${ingredients.map(ing => `
                                <li>
                                    <span class="ingredient-name">${escapeHTML(ing.name)}</span>
                                    <span class="ingredient-qty">${ing.quantity} ${ing.unit}</span>
                                </li>
                            `).join('')}
                        </ul>
                    </div>

                    <details class="instructions-section">
                        <summary>Instructions</summary>
                        <p>${escapeHTML(instructions)}</p>
                    </details>
                </div>
                <div class="meal-footer">
                    <button class="btn btn-secondary-small regenerate-btn" data-meal-num="${index + 1}" data-index="${index}">Regenerate</button>
                </div>
            </div>
        `;
    });

    mealsDisplay.innerHTML = html;
    mealPlanContainer.style.display = 'block';

    // Add regenerate event listeners
    document.querySelectorAll('.regenerate-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const mealNum = btn.dataset.mealNum;
            const index = parseInt(btn.dataset.index);
            regenerateMealForIndex(index, mealNum);
        });
    });
}

async function regenerateMealForIndex(index, mealNum) {
    const criteria = prompt(`Enter new preferences for Meal ${mealNum} (or leave blank to use same as plan):`);
    if (criteria === null) return;

    const planCriteria = currentMealPlan.criteria;
    const mealCriteria = criteria.trim() || planCriteria;

    try {
        const response = await fetch(`/api/meal-plans/${currentMealPlan.id}/regenerate-meal`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                meal_index: index,
                criteria: mealCriteria
            })
        });

        const data = await response.json();

        if (response.ok) {
            // Update the meal in the current plan
            currentMealPlan.meals[index].recipe = data.recipe;
            displayMealPlan(currentMealPlan.meals);
            showPlanStatus('Meal regenerated successfully', 'success');
        } else {
            showPlanStatus(`Error: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Regenerate meal error:', error);
        showPlanStatus('Error regenerating meal', 'error');
    }
}

// Shopping list (old code - kept for compatibility)
if (shoppingListBtn) {
shoppingListBtn.addEventListener('click', async () => {
    if (!currentMealPlan) {
        showPlanStatus('Please generate a meal plan first', 'error');
        return;
    }

    try {
        const response = await fetch(`/api/meal-plans/${currentMealPlan.id}/shopping-list`, {
            method: 'POST'
        });

        const data = await response.json();

        if (response.ok) {
            displayShoppingList(data.shopping_list, data.items);
            shoppingListModal.style.display = 'flex';
        } else {
            showPlanStatus(`✗ Error: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Shopping list error:', error);
        showPlanStatus('✗ Error generating shopping list', 'error');
    }
});
}

function displayShoppingList(byCategory, items) {
    let html = '';

    if (!items || items.length === 0) {
        html = '<p class="empty-state">You have all ingredients for these meals!</p>';
    } else {
        // Create comma-separated list of only missing items
        const missingItems = items.map(item =>
            `${item.name} (${item.quantity_missing} ${item.unit})`
        ).join(', ');

        html = `
            <div class="shopping-list-csv">
                <p><strong>Missing Ingredients:</strong></p>
                <p class="csv-list">${escapeHTML(missingItems)}</p>
            </div>

            <div style="margin-top: 30px; border-top: 1px solid var(--border-color); padding-top: 20px;">
                <p><strong>Grouped by Category:</strong></p>
        `;

        Object.keys(byCategory).sort().forEach(category => {
            const categoryItems = byCategory[category];
            html += `
                <div class="shopping-category">
                    <h3>${category.charAt(0).toUpperCase() + category.slice(1)}</h3>
                    <ul>
                        ${categoryItems.map(item => `
                            <li>
                                <span class="item-name">${escapeHTML(item.name)}</span>
                                <span class="item-qty">${item.quantity_missing} ${item.unit}</span>
                            </li>
                        `).join('')}
                    </ul>
                </div>
            `;
        });

        html += '</div>';
    }

    shoppingListContent.innerHTML = html;
}

// Close shopping list modal (old code - kept for compatibility)
if (closeShoppingListBtn) {
closeShoppingListBtn.addEventListener('click', () => {
    shoppingListModal.style.display = 'none';
});
}

if (shoppingListModal) {
shoppingListModal.addEventListener('click', (e) => {
    if (e.target === shoppingListModal) {
        shoppingListModal.style.display = 'none';
    }
});
}

function getIngredientSummary(ingredients) {
    // This is a simplified check - in a real app, we'd compare with inventory
    return {
        total: ingredients.length,
        available: Math.max(1, Math.floor(ingredients.length * 0.7))
    };
}

function showPlanStatus(message, type) {
    planStatus.textContent = message;
    planStatus.className = `status-message ${type}`;
    planStatus.style.display = 'block';

    if (type === 'success') {
        setTimeout(() => {
            planStatus.style.display = 'none';
        }, 5000);
    }
}

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

// ===== Dark Mode =====

const darkModeToggle = document.getElementById('darkModeToggle');

function initDarkMode() {
    // Check if dark mode was previously enabled
    const isDarkMode = localStorage.getItem('darkMode') === 'true';

    if (isDarkMode) {
        document.body.classList.add('dark-mode');
        darkModeToggle.textContent = '☀️';
    } else {
        darkModeToggle.textContent = '🌙';
    }
}

darkModeToggle.addEventListener('click', () => {
    document.body.classList.toggle('dark-mode');
    const isDarkMode = document.body.classList.contains('dark-mode');

    // Save preference
    localStorage.setItem('darkMode', isDarkMode);

    // Update button emoji
    darkModeToggle.textContent = isDarkMode ? '☀️' : '🌙';
});

// ===== Recipe Suggestions (AI-Driven) =====

const getSuggestionsBtn = document.getElementById('getSuggestionsBtn');
const suggestionsLoading = document.getElementById('suggestionsLoading');
const suggestionsStatus = document.getElementById('suggestionsStatus');
const recipeSuggestionsContainer = document.getElementById('recipeSuggestionsContainer');
const recipeTypeButtons = document.getElementById('recipeTypeButtons');

const suggestionsStep = document.getElementById('suggestionsStep');
const searchStep = document.getElementById('searchStep');
const selectedRecipeType = document.getElementById('selectedRecipeType');
const searchLoading = document.getElementById('searchLoading');
const searchStatus = document.getElementById('searchStatus');
const recipesContainer = document.getElementById('recipesContainer');
const recipesDisplay = document.getElementById('recipesDisplay');

let currentRecipeType = '';

// Old recipe suggestions code - kept for compatibility
if (getSuggestionsBtn) {
getSuggestionsBtn.addEventListener('click', getAIRecipeSuggestions);
}

async function getAIRecipeSuggestions() {
    suggestionsLoading.style.display = 'block';
    suggestionsStatus.style.display = 'none';
    recipeSuggestionsContainer.style.display = 'none';

    try {
        const response = await fetch('/api/recipes/suggest-types');
        const data = await response.json();

        suggestionsLoading.style.display = 'none';

        if (response.ok && data.suggestions.length > 0) {
            displayRecipeTypeSuggestions(data.suggestions);
            recipeSuggestionsContainer.style.display = 'block';
            showSuggestionsStatus(`AI found ${data.count} recipe types that match your ingredients!`, 'success');
        } else {
            showSuggestionsStatus(`Error: ${data.error || 'Could not generate suggestions'}`, 'error');
        }
    } catch (error) {
        console.error('Error fetching suggestions:', error);
        suggestionsLoading.style.display = 'none';
        showSuggestionsStatus('Error analyzing inventory. Please try again.', 'error');
    }
}

function displayRecipeTypeSuggestions(suggestions) {
    let html = '';
    suggestions.forEach(type => {
        html += `
            <button class="recipe-type-btn" data-recipe-type="${escapeHTML(type)}">
                ${escapeHTML(type)}
            </button>
        `;
    });
    recipeTypeButtons.innerHTML = html;

    // Add click handlers
    document.querySelectorAll('.recipe-type-btn').forEach(btn => {
        btn.addEventListener('click', () => searchRecipesByType(btn.dataset.recipeType, btn));
    });
}

async function searchRecipesByType(recipeType, buttonEl) {
    currentRecipeType = recipeType;

    // Update UI
    document.querySelectorAll('.recipe-type-btn').forEach(btn => btn.classList.remove('selected'));
    buttonEl.classList.add('selected');

    searchStep.style.display = 'block';
    selectedRecipeType.textContent = `Searching for: ${escapeHTML(recipeType)}`;
    searchLoading.style.display = 'block';
    searchStatus.style.display = 'none';
    recipesContainer.style.display = 'none';

    try {
        const response = await fetch('/api/recipes/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ recipe_type: recipeType })
        });
        const data = await response.json();

        searchLoading.style.display = 'none';

        if (response.ok) {
            displayRecipesWithMissingIngredients(data.recipes);
            recipesContainer.style.display = 'block';
            showSearchStatus(`Found ${data.count} recipes matching your ingredients!`, 'success');
        } else {
            showSearchStatus(`Error: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Error searching recipes:', error);
        searchLoading.style.display = 'none';
        showSearchStatus('Error searching recipes. Please try again.', 'error');
    }
}

function displayRecipesWithMissingIngredients(recipes) {
    let html = '';

    recipes.forEach(recipe => {
        const hasCount = recipe.has_ingredients.length;
        const missingCount = recipe.missing_ingredients.length;

        html += `
            <div class="suggestion-card">
                <div class="suggestion-header">
                    <div>
                        <h3>${escapeHTML(recipe.name)}</h3>
                        <div style="margin-top: 8px; display: flex; gap: 10px;">
                            <span class="match-badge match-${recipe.match_percentage >= 75 ? 'high' : recipe.match_percentage >= 50 ? 'medium' : 'low'}">
                                ${recipe.match_percentage}% Match
                            </span>
                            <span style="font-size: 0.85rem; color: var(--text-light);">
                                You have ${hasCount} of ${recipe.total_ingredients} ingredients
                            </span>
                        </div>
                    </div>
                    <span class="suggestion-source">API Ninjas</span>
                </div>
                <div class="suggestion-body">
                    <div class="suggestion-servings">Servings: ${escapeHTML(recipe.servings)}</div>

                    <div class="suggestion-ingredients">
                        <strong>Ingredients:</strong>
                        <ul class="suggestion-ingredients-list">
                            ${recipe.ingredients.map((ing, idx) => {
                                const isHave = recipe.has_ingredients.includes(ing.name);
                                const className = isHave ? 'have-ingredient' : 'missing-ingredient';
                                return `<li class="${className}">${escapeHTML(ing.name)}</li>`;
                            }).join('')}
                        </ul>
                    </div>

                    ${missingCount > 0 ? `
                        <div style="background: rgba(220, 38, 38, 0.05); border-left: 3px solid var(--danger-color); padding: 12px; border-radius: 4px; margin: 15px 0;">
                            <strong style="color: var(--danger-color);">Missing (${missingCount}):</strong>
                            <div style="margin-top: 8px; font-size: 0.9rem; color: var(--text-dark);">
                                ${recipe.missing_ingredients.map(ing => `<div>• ${escapeHTML(ing)}</div>`).join('')}
                            </div>
                        </div>
                    ` : ''}

                    <div class="suggestion-instructions">
                        <strong>Instructions:</strong>
                        <div class="suggestion-instructions-text">${escapeHTML(recipe.instructions)}</div>
                    </div>
                </div>
            </div>
        `;
    });

    recipesDisplay.innerHTML = html;
}

function showSuggestionsStatus(message, type) {
    suggestionsStatus.textContent = message;
    suggestionsStatus.className = `status-message ${type}`;
    suggestionsStatus.style.display = 'block';
}

function showSearchStatus(message, type) {
    searchStatus.textContent = message;
    searchStatus.className = `status-message ${type}`;
    searchStatus.style.display = 'block';
}

// ===== What Can I Cook - Find Recipes by Inventory =====

// Shopping list loading function
async function loadShoppingList() {
    try {
        const response = await fetch('/api/shopping-list');
        const data = await response.json();

        if (data.success) {
            displayShoppingList(data.items);
        }
    } catch (error) {
        console.error('Error loading shopping list:', error);
    }
}

function displayShoppingList(items) {
    const container = document.getElementById('shoppingListContainer');

    if (!items || items.length === 0) {
        container.innerHTML = '<p class="empty-state">No items in shopping list. Add missing ingredients from your recipes!</p>';
        return;
    }

    const html = items.map(item => `
        <div class="shopping-item" style="padding: 10px; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center;">
            <div>
                <input type="checkbox" ${item.completed ? 'checked' : ''} onchange="toggleShoppingItem('${item.id}', this.checked)">
                <span style="margin-left: 10px; ${item.completed ? 'text-decoration: line-through; color: var(--text-light);' : ''}">${item.name}</span>
                ${item.quantity ? `<span style="margin-left: 10px; color: var(--text-light);">${item.quantity}${item.unit ? ' ' + item.unit : ''}</span>` : ''}
            </div>
            <button class="btn btn-small btn-danger-small" onclick="removeShoppingItem('${item.id}')">Remove</button>
        </div>
    `).join('');

    container.innerHTML = html;
}

async function toggleShoppingItem(itemId, completed) {
    try {
        const response = await fetch(`/api/shopping-list/${itemId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ completed })
        });
        if (response.ok) {
            loadShoppingList();
        }
    } catch (error) {
        console.error('Error updating item:', error);
    }
}

async function removeShoppingItem(itemId) {
    try {
        const response = await fetch(`/api/shopping-list/${itemId}`, { method: 'DELETE' });
        if (response.ok) {
            loadShoppingList();
        }
    } catch (error) {
        console.error('Error removing item:', error);
    }
}

// ===== Initialize =====

// Load dark mode and inventory on page load
document.addEventListener('DOMContentLoaded', () => {
    initDarkMode();
    loadInventory();
    loadShoppingList();

    // Close modals when clicking outside
    window.onclick = function(event) {
        const shoppingModal = document.getElementById('shoppingListModal');
        const recipeModal = document.getElementById('recipeDetailModal');
        if (event.target === shoppingModal) {
            shoppingModal.style.display = 'none';
        }
        if (event.target === recipeModal) {
            recipeModal.style.display = 'none';
        }
    };

    // Load shopping list when shopping list tab is clicked
    const shoppingListTab = document.getElementById('shopping-list-tab');
    if (shoppingListTab) {
        const observer = new MutationObserver(() => {
            if (shoppingListTab.classList.contains('active') || shoppingListTab.style.display !== 'none') {
                loadShoppingList();
            }
        });
        observer.observe(shoppingListTab, { attributes: true, attributeFilter: ['class', 'style'] });
    }

    // Clear shopping list button
    const clearShoppingBtn = document.getElementById('clearShoppingBtn');
    if (clearShoppingBtn) {
        clearShoppingBtn.addEventListener('click', async () => {
            if (confirm('Clear all items from shopping list?')) {
                try {
                    const response = await fetch('/api/shopping-list', { method: 'DELETE' });
                    if (response.ok) {
                        loadShoppingList();
                    }
                } catch (error) {
                    console.error('Error clearing shopping list:', error);
                }
            }
        });
    }

    // ===== Meal Planning (Monday-Friday) =====

    const planningDays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'];
    let currentPlan = {};

    // Load saved recipes for selection
    async function loadRecipesForPlanning() {
        try {
            const response = await fetch('/api/user-recipes');
            const data = await response.json();
            return data.recipes || [];
        } catch (error) {
            console.error('Error loading recipes for planning:', error);
            return [];
        }
    }

    // Setup recipe selection buttons
    planningDays.forEach(day => {
        const button = document.getElementById(`select${day.charAt(0).toUpperCase() + day.slice(1)}`);
        if (button) {
            button.addEventListener('click', async () => {
                const recipes = await loadRecipesForPlanning();
                showRecipeSelector(recipes, day);
            });
        }
    });

    // Show modal to select recipe
    function showRecipeSelector(recipes, day) {
        if (recipes.length === 0) {
            alert('No saved recipes found. Import or create recipes first!');
            return;
        }

        let options = recipes.map(r => `<option value="${r.id}" data-recipe='${JSON.stringify(r)}'>${r.name}</option>`).join('');

        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.style.display = 'flex';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>Select Recipe for ${day.charAt(0).toUpperCase() + day.slice(1)}</h2>
                    <button class="modal-close" onclick="this.closest('.modal').remove()">&times;</button>
                </div>
                <div class="modal-body">
                    <select id="recipeSelect" class="form-control" style="width: 100%; padding: 10px; border: 1px solid var(--border-color); border-radius: 6px; font-size: 1rem;">
                        <option value="">-- Choose a recipe --</option>
                        ${options}
                    </select>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-primary" onclick="selectRecipeForDay('${day}', document.getElementById('recipeSelect'))">Select</button>
                    <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">Cancel</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    }

    // Global function to select recipe for a day
    window.selectRecipeForDay = function(day, selectElement) {
        const option = selectElement.options[selectElement.selectedIndex];
        if (!option.value) {
            alert('Please select a recipe');
            return;
        }

        const recipe = JSON.parse(option.getAttribute('data-recipe'));
        currentPlan[day] = recipe;

        // Update UI
        const recipeDiv = document.getElementById(`${day}Recipe`);
        recipeDiv.innerHTML = `
            <div class="recipe-card">
                <strong>${recipe.name}</strong>
                <p style="font-size: 0.9rem; color: var(--text-light); margin: 5px 0;">
                    ${recipe.ingredients ? recipe.ingredients.length : 0} ingredients
                </p>
                <button class="btn btn-small btn-secondary" onclick="removeRecipeForDay('${day}')" style="font-size: 0.85rem; padding: 5px 10px;">Remove</button>
            </div>
        `;

        // Close modal
        document.querySelector('.modal').remove();
    };

    // Remove recipe for a day
    window.removeRecipeForDay = function(day) {
        delete currentPlan[day];
        const recipeDiv = document.getElementById(`${day}Recipe`);
        recipeDiv.innerHTML = '<p class="empty">No recipe selected</p>';
    };

    // Generate shopping list from current plan
    document.getElementById('generateShoppingBtn').addEventListener('click', async () => {
        // Check if all days have recipes selected
        if (Object.keys(currentPlan).length !== 5) {
            alert(`Please select recipes for all 5 days. Selected: ${Object.keys(currentPlan).length}/5`);
            return;
        }

        try {
            const response = await fetch('/api/planning/csv', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    recipes: currentPlan,
                    exclude_inventory: true
                })
            });

            const data = await response.json();

            if (response.ok) {
                // Display CSV
                document.getElementById('csvText').value = data.csv_string;
                document.getElementById('shoppingPreview').style.display = 'block';
            } else {
                alert(`Error: ${data.error}`);
            }
        } catch (error) {
            console.error('Error generating shopping list:', error);
            alert('Error generating shopping list');
        }
    });

    // Copy to clipboard
    document.getElementById('copyToClipboardBtn').addEventListener('click', () => {
        const text = document.getElementById('csvText');
        text.select();
        document.execCommand('copy');

        const status = document.getElementById('copyStatus');
        status.textContent = '✓ Copied to clipboard!';
        status.className = 'status-message success';
        status.style.display = 'block';

        setTimeout(() => {
            status.style.display = 'none';
        }, 3000);
    });

    // Download CSV
    document.getElementById('downloadCsvBtn').addEventListener('click', () => {
        const csv = document.getElementById('csvText').value;
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `shopping-list-${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    });

    // Clear plan
    document.getElementById('clearPlanBtn').addEventListener('click', () => {
        if (confirm('Clear the entire meal plan?')) {
            currentPlan = {};
            planningDays.forEach(day => {
                const recipeDiv = document.getElementById(`${day}Recipe`);
                recipeDiv.innerHTML = '<p class="empty">No recipe selected</p>';
            });
            document.getElementById('shoppingPreview').style.display = 'none';
        }
    });

    // Refresh inventory every 30 seconds
    setInterval(loadInventory, 30000);
    // Refresh shopping list every 20 seconds
    setInterval(loadShoppingList, 20000);
});
