from datetime import datetime, timedelta

class VideoStore:
    def __init__(self, datastore_client):
        self.ds = datastore_client

    def fetch_videos(self, date_assigned=None):
        query = self.ds.query(kind="Video")
        if date_assigned:
            query.add_filter("date_assigned", ">", datetime.strptime(date_assigned, "%Y-%m-%d %H:%M:%S.%f"))
            query.add_filter("date_assigned", "<", datetime.strptime(date_assigned, "%Y-%m-%d %H:%M:%S.%f") + timedelta(days=1))
        query.order = ["date_assigned"]
        videos = query.fetch()
        return list(videos)
