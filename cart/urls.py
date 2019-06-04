from django.urls import path,include
from cart import views
urlpatterns = [
    path('add/', views.CartAddView.as_view(), name='cart_add'),             # 添加购物车视图
    path('delete/', views.CartDeleteView.as_view(), name='cart_del'),       # 删除购物车视图
    path('update/', views.CartUpdateView.as_view(), name='cart_update'),    # 更新购物车视图
    path('', views.CartInfoView.as_view(), name='cart_info'),               # 展示用户购物车
]
