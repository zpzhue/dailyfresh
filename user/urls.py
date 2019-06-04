from django.urls import path,include
from . import views
urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),           # 用户注册url
    path('login/', views.LoginView.as_view(), name='login'),                    # 用户登陆url
    path('logout/', views.LogoutView.as_view(), name='logout'),                 # 用户注销url
    path('active/<token>', views.ActiveRegisterView.as_view(), name='login'),   # 激活用户url
    path('', views.UserInfoView.as_view(), name= 'user'),                       # 用户中心-用户信息页
    path('order/<int:page>/', views.OrderView.as_view(), name= 'order'),         # 用户中心-用户信息页
    path('order/', views.OrderView.as_view(), name= 'order'),                   # 用户中心-用户信息页
    path('address/', views.AddressView.as_view(), name= 'address')              # 用户中心-用户信息页
]
