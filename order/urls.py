from django.urls import path,include
from order import views

urlpatterns = [
    path('place/', views.OrderPlaceView.as_view(), name='place'),
    path('commit/', views.OrderCommitView.as_view(), name='commit'),
    path('order_pay/', views.OrderPayView.as_view(), name='order_pay'),
]
