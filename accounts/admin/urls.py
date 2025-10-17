from django.urls import path


urlpatterns = [
    path('make-this-user-staff/',UserStaff.as_View(),name='staffuser')
    ]
