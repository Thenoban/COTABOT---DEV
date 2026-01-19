/**
 * Search and Filter Utilities
 */

class SearchFilter {
    constructor(data, fields) {
        this.originalData = data;
        this.filteredData = data;
        this.searchFields = fields; // Fields to search in
        this.filters = {};
    }

    /**
     * Search across specified fields
     */
    search(query) {
        if (!query || query.trim() === '') {
            this.filteredData = this.originalData;
            return this.filteredData;
        }

        const lowerQuery = query.toLowerCase();

        this.filteredData = this.originalData.filter(item => {
            return this.searchFields.some(field => {
                const value = this.getNestedValue(item, field);
                return String(value).toLowerCase().includes(lowerQuery);
            });
        });

        return this.filteredData;
    }

    /**
     * Apply filter
     */
    applyFilter(filterName, filterFn) {
        this.filters[filterName] = filterFn;
        this.updateFiltered();
        return this.filteredData;
    }

    /**
     * Remove filter
     */
    removeFilter(filterName) {
        delete this.filters[filterName];
        this.updateFiltered();
        return this.filteredData;
    }

    /**
     * Clear all filters
     */
    clearFilters() {
        this.filters = {};
        this.filteredData = this.originalData;
        return this.filteredData;
    }

    /**
     * Update filtered data based on active filters
     */
    updateFiltered() {
        this.filteredData = this.originalData;

        Object.values(this.filters).forEach(filterFn => {
            this.filteredData = this.filteredData.filter(filterFn);
        });
    }

    /**
     * Sort data
     */
    sort(field, direction = 'asc') {
        this.filteredData.sort((a, b) => {
            const aVal = this.getNestedValue(a, field);
            const bVal = this.getNestedValue(b, field);

            if (aVal < bVal) return direction === 'asc' ? -1 : 1;
            if (aVal > bVal) return direction === 'asc' ? 1 : -1;
            return 0;
        });

        return this.filteredData;
    }

    /**
     * Get nested object value by path (e.g., 'user.name')
     */
    getNestedValue(obj, path) {
        return path.split('.').reduce((current, prop) => {
            return current?.[prop];
        }, obj) ?? '';
    }

    /**
     * Get current filtered data
     */
    getData() {
        return this.filteredData;
    }

    /**
     * Update original data
     */
    setData(data) {
        this.originalData = data;
        this.updateFiltered();
    }
}

/**
 * Debounce function for search input
 */
function debounce(func, wait = 300) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
