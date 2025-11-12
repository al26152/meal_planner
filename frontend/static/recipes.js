// Recipe Management Functions
const recipeManager = {
    // Switch between import modes (URL vs Paste)
    switchImportMode: function(mode) {
        const urlMode = document.getElementById('urlImportMode');
        const pasteMode = document.getElementById('pasteImportMode');
        const buttons = document.querySelectorAll('.tab-like-btn');

        buttons.forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');

        if (mode === 'url') {
            urlMode.style.display = 'block';
            pasteMode.style.display = 'none';
        } else {
            urlMode.style.display = 'none';
            pasteMode.style.display = 'block';
        }
    },

    // Parse pasted recipe text
    parseRecipeFromText: async function() {
        const recipeText = document.getElementById('recipeText').value.trim();
        const tagsInput = document.getElementById('recipeTextTags').value.trim();
        const tags = tagsInput ? tagsInput.split(',').map(t => t.trim()) : [];

        if (!recipeText) {
            this.showStatus('Please paste a recipe', 'error');
            return;
        }

        try {
            this.showStatus('Parsing recipe...', 'loading');

            const response = await fetch('/api/recipes/import', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    content: recipeText,
                    tags: tags
                })
            });

            const data = await response.json();

            if (data.success) {
                // Show edit modal before saving
                this.showEditRecipeModal(data.recipe, tags, true);
                this.showStatus('', '');
            } else {
                this.showStatus(`Error: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('Error parsing recipe:', error);
            this.showStatus('Failed to parse recipe', 'error');
        }
    },

    // Show edit modal for recipe (allows user to amend before saving)
    showEditRecipeModal: function(recipe, tags, isFromPaste = false) {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.id = 'editRecipeModal';
        modal.style.display = 'flex';

        const ingredientsList = recipe.ingredients.map((ing, i) => `
            <div class="ingredient-input-row" data-index="${i}">
                <input type="text" class="ingredient-name" placeholder="Ingredient name" value="${ing.name || ''}" />
                <input type="number" class="ingredient-qty" placeholder="Qty" value="${ing.quantity || 1}" step="0.5" />
                <input type="text" class="ingredient-unit" placeholder="Unit" value="${ing.unit || ''}" />
                <button type="button" class="btn btn-small btn-danger-small" onclick="recipeManager.removeIngredient(${i})">Remove</button>
            </div>
        `).join('');

        modal.innerHTML = `
            <div class="modal-content large">
                <div class="modal-header">
                    <h2>Edit Recipe Before Saving</h2>
                    <button class="modal-close" onclick="document.getElementById('editRecipeModal').remove()">&times;</button>
                </div>
                <div class="modal-body">
                    <p style="color: var(--text-light); margin-bottom: 15px;">Review and edit the parsed recipe. Feel free to change anything!</p>

                    <div class="form-group">
                        <label>Recipe Name:</label>
                        <input type="text" id="editRecipeName" class="recipe-input" value="${recipe.name || ''}" placeholder="Recipe name" />
                    </div>

                    <div class="form-group">
                        <label>Instructions:</label>
                        <textarea id="editRecipeInstructions" class="recipe-textarea" placeholder="Cooking instructions...">${recipe.instructions || ''}</textarea>
                    </div>

                    <div class="form-group">
                        <label>Ingredients:</label>
                        <div id="editIngredientsInputs" class="ingredients-inputs">
                            ${ingredientsList || '<p style="color: var(--text-light);">No ingredients parsed. Add some below.</p>'}
                        </div>
                        <button type="button" class="btn btn-small" onclick="recipeManager.addIngredientInput()">+ Add Ingredient</button>
                    </div>

                    <div class="form-group">
                        <label>Tags (comma-separated):</label>
                        <input type="text" id="editRecipeTags" class="recipe-input" value="${(tags || recipe.tags || []).join(', ')}" />
                    </div>

                    <div class="form-buttons" style="display: flex; gap: 10px; margin-top: 20px;">
                        <button class="btn btn-primary" onclick="recipeManager.saveEditedRecipe()">Save Recipe</button>
                        <button class="btn btn-secondary" onclick="document.getElementById('editRecipeModal').remove()">Cancel</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
    },

    // Save edited recipe
    saveEditedRecipe: async function() {
        const name = document.getElementById('editRecipeName').value.trim();
        const instructions = document.getElementById('editRecipeInstructions').value.trim();
        const tagsInput = document.getElementById('editRecipeTags').value.trim();
        const tags = tagsInput ? tagsInput.split(',').map(t => t.trim()) : [];

        if (!name) {
            alert('Please enter a recipe name');
            return;
        }

        // Collect ingredients
        const ingredients = [];
        document.querySelectorAll('#editIngredientsInputs .ingredient-input-row').forEach(row => {
            const ingName = row.querySelector('.ingredient-name').value.trim();
            const qty = parseFloat(row.querySelector('.ingredient-qty').value) || 1;
            const unit = row.querySelector('.ingredient-unit').value.trim();

            if (ingName) {
                ingredients.push({ name: ingName, quantity: qty, unit });
            }
        });

        if (ingredients.length === 0) {
            alert('Please add at least one ingredient');
            return;
        }

        try {
            this.showStatus('Saving recipe...', 'loading');

            // Save using the regular add recipe endpoint
            const response = await fetch('/api/user-recipes', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name,
                    ingredients,
                    instructions,
                    tags,
                    source: 'manual'
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showStatus('Recipe saved successfully!', 'success');
                document.getElementById('editRecipeModal').remove();
                // Clear paste mode
                document.getElementById('recipeText').value = '';
                document.getElementById('recipeTextTags').value = '';
                this.loadRecipes();
            } else {
                this.showStatus(`Error: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('Error saving recipe:', error);
            this.showStatus('Failed to save recipe', 'error');
        }
    },

    // Load all recipes and display them
    loadRecipes: async function(searchQuery = '') {
        try {
            const url = searchQuery
                ? `/api/user-recipes?q=${encodeURIComponent(searchQuery)}`
                : '/api/user-recipes';

            const response = await fetch(url);
            const data = await response.json();

            if (data.success) {
                this.displayRecipes(data.recipes);
            } else {
                this.showStatus('Error loading recipes', 'error');
            }
        } catch (error) {
            console.error('Error loading recipes:', error);
            this.showStatus('Failed to load recipes', 'error');
        }
    },

    // Display recipes in the library
    displayRecipes: function(recipes) {
        const container = document.getElementById('recipesLibraryContainer');
        const countEl = document.getElementById('recipeCount');

        countEl.textContent = `${recipes.length} recipe${recipes.length !== 1 ? 's' : ''}`;

        if (recipes.length === 0) {
            container.innerHTML = '<p class="empty-state">No recipes found. Import one to get started!</p>';
            return;
        }

        container.innerHTML = recipes.map(recipe => `
            <div class="recipe-card">
                <div class="recipe-card-header">
                    <h3>${recipe.name}</h3>
                    <span class="recipe-source">${recipe.source || 'manual'}</span>
                </div>
                <div class="recipe-card-body">
                    ${recipe.tags && recipe.tags.length > 0 ? `
                        <div class="recipe-tags">
                            ${recipe.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                        </div>
                    ` : ''}
                    <p class="recipe-ingredients">
                        ${recipe.ingredients.length} ingredients
                    </p>
                </div>
                <div class="recipe-card-footer">
                    <button class="btn btn-small" onclick="recipeManager.viewRecipe('${recipe.id}')">
                        View & Adapt
                    </button>
                    <button class="btn btn-small btn-danger-small" onclick="recipeManager.deleteRecipe('${recipe.id}')">
                        Delete
                    </button>
                </div>
            </div>
        `).join('');
    },

    // View recipe details and show adaptation
    viewRecipe: async function(recipeId) {
        try {
            const response = await fetch(`/api/user-recipes/${recipeId}/adapt`);
            const data = await response.json();

            console.log('Recipe adapt response:', data);

            if (data.success) {
                const recipe = data.recipe;
                const adaptation = recipe.adaptation;

                let html = `
                    <div class="recipe-details">
                        <div class="recipe-meta">
                            <p><strong>Source:</strong> ${recipe.source || 'manual'}</p>
                            ${recipe.source_url ? `<p><strong>URL:</strong> <a href="${recipe.source_url}" target="_blank">View Original</a></p>` : ''}
                        </div>

                        <h3>Ingredients</h3>
                        <div class="recipe-ingredients-list">
                            ${recipe.ingredients && recipe.ingredients.length > 0 ? recipe.ingredients.map(ing => `
                                <div class="ingredient-item">
                                    <span>${ing.name}</span>
                                    <span class="ingredient-qty">${ing.quantity} ${ing.unit || ''}</span>
                                </div>
                            `).join('') : '<p style="color: var(--text-light);">No ingredients specified</p>'}
                        </div>

                        <h3>Instructions</h3>
                        <div class="recipe-instructions">
                            <p>${recipe.instructions || 'No instructions available'}</p>
                        </div>
                `;

                // Show adaptation info if available
                if (adaptation) {
                    html += `
                        <div class="adaptation-info ${adaptation.can_make ? 'can-make' : 'cannot-make'}">
                            <h3>📊 Adaptation to Your Inventory</h3>
                            <p><strong>Can Make:</strong> ${adaptation.can_make ? '✅ Yes' : '❌ No'}</p>
                            <p><strong>Match Score:</strong> ${adaptation.match_percentage}%</p>

                            ${adaptation.substitutions && adaptation.substitutions.length > 0 ? `
                                <div class="substitutions">
                                    <h4>🔄 Suggested Substitutions:</h4>
                                    <ul>
                                        ${adaptation.substitutions.map(sub => `
                                            <li><strong>${sub.original}</strong> → <strong>${sub.substitute}</strong> (${sub.reason})</li>
                                        `).join('')}
                                    </ul>
                                </div>
                            ` : ''}

                            ${adaptation.adaptations && adaptation.adaptations.length > 0 ? `
                                <div class="adaptations">
                                    <h4>⚙️ Adaptations Needed:</h4>
                                    <ul>
                                        ${adaptation.adaptations.map(adapt => `<li>${adapt}</li>`).join('')}
                                    </ul>
                                </div>
                            ` : ''}

                            ${adaptation.missing_ingredients && adaptation.missing_ingredients.length > 0 ? `
                                <div class="missing">
                                    <h4>🛒 Missing Ingredients:</h4>
                                    <p>${adaptation.missing_ingredients.join(', ')}</p>
                                </div>
                            ` : ''}

                            ${adaptation.notes ? `
                                <div class="notes">
                                    <p><strong>Notes:</strong> ${adaptation.notes}</p>
                                </div>
                            ` : ''}
                        </div>
                    `;
                }

                html += '</div>';

                document.getElementById('recipeDetailTitle').textContent = recipe.name;
                document.getElementById('recipeDetailContent').innerHTML = html;
                document.getElementById('recipeDetailModal').style.display = 'flex';
            } else {
                console.error('Recipe adapt failed:', data);
                // Show error in modal instead of status area
                const modal = document.getElementById('recipeDetailModal');
                document.getElementById('recipeDetailTitle').textContent = 'Error';
                document.getElementById('recipeDetailContent').innerHTML = `<p style="color: var(--danger-color);">Failed to load recipe: ${data.error || 'Unknown error'}</p>`;
                modal.style.display = 'flex';
            }
        } catch (error) {
            console.error('Error viewing recipe:', error);
            // Show error in modal instead of status area
            const modal = document.getElementById('recipeDetailModal');
            document.getElementById('recipeDetailTitle').textContent = 'Error';
            document.getElementById('recipeDetailContent').innerHTML = `<p style="color: var(--danger-color);">Failed to load recipe: ${error.message}</p>`;
            modal.style.display = 'flex';
        }
    },

    // Delete a recipe
    deleteRecipe: async function(recipeId) {
        if (!confirm('Are you sure you want to delete this recipe?')) {
            return;
        }

        try {
            const response = await fetch(`/api/user-recipes/${recipeId}`, {
                method: 'DELETE'
            });
            const data = await response.json();

            if (data.success) {
                this.showStatus('Recipe deleted successfully', 'success');
                this.loadRecipes();
            } else {
                this.showStatus('Error deleting recipe', 'error');
            }
        } catch (error) {
            console.error('Error deleting recipe:', error);
            this.showStatus('Failed to delete recipe', 'error');
        }
    },

    // Import recipe from URL
    importRecipe: async function() {
        const url = document.getElementById('recipeUrl').value.trim();
        const tagsInput = document.getElementById('recipeTags').value.trim();
        const tags = tagsInput ? tagsInput.split(',').map(t => t.trim()) : [];

        if (!url) {
            this.showStatus('Please enter a recipe URL', 'error');
            return;
        }

        try {
            this.showStatus('Importing recipe...', 'loading');

            const response = await fetch('/api/recipes/import', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    url: url,
                    tags: tags
                })
            });

            const data = await response.json();

            if (data.success && data.needs_manual_entry) {
                // Recipe needs manual completion (e.g., visual-only YouTube videos)
                this.showManualEntryForm(data.recipe, data.message, tags);
            } else if (data.success) {
                this.showStatus('Recipe imported successfully!', 'success');
                document.getElementById('recipeUrl').value = '';
                document.getElementById('recipeTags').value = '';
                this.loadRecipes();
            } else {
                this.showStatus(`Error: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('Error importing recipe:', error);
            this.showStatus('Failed to import recipe', 'error');
        }
    },

    // Add ingredient input row (used in edit modal)
    addIngredientInput: function() {
        const container = document.getElementById('editIngredientsInputs') || document.getElementById('ingredientsInputs');
        if (!container) return;

        const index = container.querySelectorAll('.ingredient-input-row').length;
        const row = document.createElement('div');
        row.className = 'ingredient-input-row';
        row.innerHTML = `
            <input type="text" class="ingredient-name" placeholder="Ingredient name" />
            <input type="number" class="ingredient-qty" placeholder="Qty" step="0.5" value="1" />
            <input type="text" class="ingredient-unit" placeholder="Unit" />
            <button type="button" class="btn btn-small btn-danger-small" onclick="recipeManager.removeIngredient(${index})">Remove</button>
        `;
        container.appendChild(row);
    },

    // Remove ingredient input row
    removeIngredient: function(index) {
        const row = document.querySelector(`.ingredient-input-row[data-index="${index}"]`);
        if (row) {
            row.remove();
        }
    },

    // Show status message
    showStatus: function(message, type) {
        const statusEl = document.getElementById('importStatus');
        statusEl.textContent = message;
        statusEl.className = `status-message ${type}`;

        if (type !== 'loading') {
            setTimeout(() => {
                statusEl.textContent = '';
                statusEl.className = 'status-message';
            }, 3000);
        }
    }
};

// Initialize event listeners when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Import recipe button
    const importBtn = document.getElementById('importRecipeBtn');
    if (importBtn) {
        importBtn.addEventListener('click', () => recipeManager.importRecipe());
    }

    // Parse recipe button
    const parseBtn = document.getElementById('parseRecipeBtn');
    if (parseBtn) {
        parseBtn.addEventListener('click', () => recipeManager.parseRecipeFromText());
    }

    // Recipe search
    const searchInput = document.getElementById('recipeSearch');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            recipeManager.loadRecipes(e.target.value);
        });
    }

    // Close recipe detail modal
    const closeBtn = document.getElementById('closeRecipeDetailBtn');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            document.getElementById('recipeDetailModal').style.display = 'none';
        });
    }

    // Load recipes when recipes tab is selected
    const recipesTab = document.getElementById('recipes-tab');
    if (recipesTab) {
        // Check if tab becomes visible and load recipes
        const observer = new MutationObserver(() => {
            if (recipesTab.classList.contains('active') || recipesTab.style.display !== 'none') {
                recipeManager.loadRecipes();
                observer.disconnect(); // Only observe once
            }
        });

        observer.observe(recipesTab, { attributes: true, attributeFilter: ['class', 'style'] });
    }

    // Load recipes on first load
    recipeManager.loadRecipes();
});

// Allow Enter key to import recipe
document.addEventListener('keypress', function(e) {
    if (e.key === 'Enter' && document.getElementById('recipeUrl') === document.activeElement) {
        recipeManager.importRecipe();
    }
});
