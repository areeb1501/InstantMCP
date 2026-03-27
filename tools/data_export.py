# Data Export Tool

class DataExportTool:
    """A simple tool to export data in CSV format."""

    def __init__(self, data):
        self.data = data

    def export_to_csv(self, file_path):
        import csv
        with open(file_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            for row in self.data:
                writer.writerow(row)
        return f"Data exported successfully to {file_path}"
