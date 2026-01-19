/**
 * Data Exporter Utility
 * Export data to CSV, JSON formats
 */

class DataExporter {
    /**
     * Export array of objects to CSV
     */
    exportToCSV(data, filename = 'export.csv') {
        if (!data || data.length === 0) {
            toast.warning('No data to export');
            return;
        }

        const csv = this.convertToCSV(data);
        this.download(csv, filename, 'text/csv;charset=utf-8;');
        toast.success(`Exported ${data.length} records to ${filename}`);
    }

    /**
     * Export data to JSON
     */
    exportToJSON(data, filename = 'export.json') {
        if (!data || data.length === 0) {
            toast.warning('No data to export');
            return;
        }

        const json = JSON.stringify(data, null, 2);
        this.download(json, filename, 'application/json');
        toast.success(`Exported ${data.length} records to ${filename}`);
    }

    /**
     * Convert array of objects to CSV string
     */
    convertToCSV(data) {
        if (data.length === 0) return '';

        // Get headers from first object
        const headers = Object.keys(data[0]);

        // Create CSV header row
        const headerRow = headers.map(h => this.escapeCSV(h)).join(',');

        // Create data rows
        const dataRows = data.map(row => {
            return headers.map(header => {
                const value = row[header];
                return this.escapeCSV(value);
            }).join(',');
        });

        return [headerRow, ...dataRows].join('\n');
    }

    /**
     * Escape CSV field value
     */
    escapeCSV(value) {
        if (value === null || value === undefined) return '';

        const str = String(value);

        // If contains comma, quote, or newline, wrap in quotes and escape quotes
        if (str.includes(',') || str.includes('"') || str.includes('\n')) {
            return `"${str.replace(/"/g, '""')}"`;
        }

        return str;
    }

    /**
     * Trigger file download
     */
    download(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.style.display = 'none';

        document.body.appendChild(a);
        a.click();

        // Cleanup
        setTimeout(() => {
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }, 100);
    }
}

// Global exporter instance
const exporter = new DataExporter();
