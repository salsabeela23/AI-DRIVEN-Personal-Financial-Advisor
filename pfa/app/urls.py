from django.urls import path
from . import views

urlpatterns = [
    path('', views.getStarted, name='get_started'),
    path('get-started/', views.getStarted, name='get_started'),
    path('send_alert_email/', views.trigger_alert_email, name='send_alert_email'),
    path('signup/', views.signup_view, name='signup'),
    path('signin/', views.signin_view, name='signin'),
    path('investment_advice/', views.investment_advice, name='investment_advice'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/logout', views.dashboardLogout, name='dashboardLogout'),
    path('add_expense/', views.add_expense, name='add_expense'),
    path('delete_expense/', views.delete_expense, name='delete_expense'),
    path('add-income/', views.add_income, name='add_income'),
    path('delete-income/', views.delete_income, name='delete_income'),
    path('logout/', views.logout_view, name='logout'),
    path('logged_out/', views.logged_out_view, name='logged_out'),
]
