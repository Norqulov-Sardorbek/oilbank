from django.db import models





class EduVideo(models.Model):
    class VideoType(models.TextChoices):
        URL = "url", "Url"
        FILE = "file", "File"
    title = models.CharField(max_length=255)
    description = models.TextField()
    video_type = models.CharField(max_length=20, choices=VideoType.choices, default=VideoType.URL)
    video_url = models.URLField(null=True, blank=True)
    video_file = models.FileField(upload_to="edu_videos/", null=True, blank=True)
    
    @property
    def file_size(self):
        if self.video_file:
            return round(self.video_file.size / (1024 * 1024), 2)
        return None
    