from django.urls import path
from . import views

urlpatterns = [
    path('', views.chatbot_page, name='chatbot'),
    path('api/', views.chat_api, name='chat_api'),
    path('documents/', views.manage_documents, name='manage_documents'),
    path('documents/upload/', views.upload_documents, name='upload_documents'),
    path('documents/delete/<int:doc_id>/', views.delete_document, name='delete_document'),
]
