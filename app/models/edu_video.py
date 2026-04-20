from django.db import models



class VideoCategory(models.Model):
    name_uz = models.CharField(max_length=255)
    name_ru = models.CharField(max_length=255, null=True, blank=True)
    name_en = models.CharField(max_length=255, null=True, blank=True)
    



class EduVideo(models.Model):
    class VideoType(models.TextChoices):
        URL = "url", "Url"
        FILE = "file", "File"
    category = models.ForeignKey(VideoCategory, on_delete=models.CASCADE, related_name="videos")
    title_uz = models.CharField(max_length=255)
    title_ru = models.CharField(max_length=255, null=True, blank=True)
    title_en = models.CharField(max_length=255, null=True, blank=True)
    description_uz = models.TextField()
    description_ru = models.TextField(null=True, blank=True)
    description_en = models.TextField(null=True, blank=True)
    video_type = models.CharField(max_length=20, choices=VideoType.choices, default=VideoType.URL)
    video_url = models.URLField(null=True, blank=True)
    video_file = models.FileField(upload_to="edu_videos/", null=True, blank=True)
    
    @property
    def file_size(self):
        if self.video_file:
            return round(self.video_file.size / (1024 * 1024), 2)
        return None
    