from .base_stats import BaseStats
import textwrap
import psutil
import datetime

class MemoryStats(BaseStats):
    """
    Represents memory statistics.

    Attributes:
        time_stamp (datetime): The timestamp of the last update.
        total (float): The last recorded total memory.
        available (float): The last recorded available memory.
        used (float): The last recorded used memory.
        percent (float): The last recorded memory usage percentage.
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
        self.total = None
        self.available = None
        self.used = None
        self.percent = None

    def update(self):
        """
        Updates the memory statistics.
        """

        self.time_stamp = datetime.datetime.now()
        self.total = self.memory_info("total")
        self.free = self.memory_info("free")
        self.used = self.memory_info("used")
        self.percent = self.memory_info("percent")

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
            "total": self.total,
            "free": self.free,
            "used": self.used,
            "percent": self.percent
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
            count=self.total,
            free=self.free,
            used=self.used,
            percent=self.percent
        )
        return template
