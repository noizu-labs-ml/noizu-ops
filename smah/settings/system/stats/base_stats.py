import datetime

class BaseStats:
    def __init__(self):
        """
        Initializes the DiskStats instance.
        """
        self.time_stamp = None

    def stale(self, threshold = 100):
        """
        Checks if the disk statistics are stale based on the given threshold.

        Args:
            threshold (int): The threshold in microseconds.

        Returns:
            bool: True if the statistics are stale, False otherwise.
        """
        if self.time_stamp is None:
            return True
        else:
            return (datetime.datetime.now().microsecond - self.time_stamp.microsecond) > threshold