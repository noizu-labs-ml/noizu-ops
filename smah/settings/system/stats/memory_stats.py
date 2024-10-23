from .base_stats import BaseStats
import textwrap
import psutil
import datetime

class MemoryStats(BaseStats):
    """
    Represents memory statistics.

    Attributes:
        time_stamp (datetime): The timestamp of the last update.
        last_total (float): The last recorded total memory.
        last_available (float): The last recorded available memory.
        last_used (float): The last recorded used memory.
        last_percent (float): The last recorded memory usage percentage.
    """

    @staticmethod
    def memory_info(reading):
        """
        Retrieves memory information based on the specified reading type.

        Args:
            reading (str): The type of memory information to retrieve.

        Returns:
            float: The requested memory information.
        """
        try:
            if reading == "total":
                return round(psutil.virtual_memory().total / (1024.0 ** 3), 2)
            elif reading == "free":
                return round(psutil.virtual_memory().available / (1024.0 ** 3), 2)
            elif reading == "used":
                return round(psutil.virtual_memory().used / (1024.0 ** 3), 2)
            elif reading == "percent":
                return psutil.virtual_memory().percent
        except:
            return None

    def __init__(self):
        """
        Initializes the MemoryStats instance.
        """
        super().__init__()
        self.last_total = None
        self.last_available = None
        self.last_used = None
        self.last_percent = None

    def update(self):
        """
        Updates the memory statistics.
        """

        self.time_stamp = datetime.datetime.now()
        self.last_total = self.memory_info("total")
        self.last_free = self.memory_info("free")
        self.last_used = self.memory_info("used")
        self.last_percent = self.memory_info("percent")

    def readings(self, threshold=100):
        """
        Retrieves the current memory readings, updating if necessary.

        Args:
            threshold (int): The threshold in microseconds.

        Returns:
            dict: The current memory readings.
        """

        if self.stale(threshold):
            self.update()
        return {
            "time": self.time_stamp,
            "total": self.last_total,
            "free": self.last_free,
            "used": self.last_used,
            "percent": self.last_percent
        }

    def show(self, options=None):
        if self.stale():
            self.update()
        template = textwrap.dedent(
            """
            - time: {time}
            - total: {total}
            - free: {free}
            - used: {used}
            - percent: {percent}
            """
        ).strip().format(
            time=self.time_stamp,
            count=self.last_total,
            free=self.last_free,
            used=self.last_used,
            percent=self.last_percent
        )
        return template
