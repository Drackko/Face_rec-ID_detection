from django.urls import path
from . import views

urlpatterns = [
    path('show_data/', views.my_view),
    path('',views.home,name='home'),
    path('detections/',views.detection_view,name='detection'),
    path('camera_id/',views.camera_id,name='camera_id'),
    path('api/cameras/', views.get_data, name='camera_data'),
    path('save-data/', views.save_data_view, name='save_data'),
    path('delete-data/<int:index>/', views.delete_data, name='delete_data'),
]   