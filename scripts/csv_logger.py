import csv
import os
from datetime import datetime


class CSVLogger:
    def __init__(self, file_name="debug.csv", folder="debug_logs"):
        os.makedirs(folder, exist_ok=True)
        self.file_path = os.path.join(folder, file_name)

    def append(self, data: dict):
        """
        Append dictionary data to CSV.
        Headers auto-created from keys.
        """
        file_exists = os.path.isfile(self.file_path)

        with open(self.file_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=data.keys())

            if not file_exists:
                writer.writeheader()

            writer.writerow(data)

    def append_with_timestamp(self, data: dict):
        data["timestamp"] = datetime.now().isoformat()
        self.append(data)