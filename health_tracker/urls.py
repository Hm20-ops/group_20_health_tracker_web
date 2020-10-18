from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from . import views
# # the prefix to all these URLs is 'accounts/' - it comes from the top level urls.py
#from .views import PostsListsView



urlpatterns = [
	path('home/', views.home, name='home'),
	path('', auth_views.LoginView.as_view(template_name='login.html',
										  redirect_authenticated_user=True), name='signin'),
	path('login/', views.login, name='login'),
	path('logout/', auth_views.LogoutView.as_view(template_name='login.html'), name='logout'),
	path('create/', views.create_user, name='create'),
	path('check_username/', views.username_exists, name='check_username'),
	path('activate/<uidb64>/<token>/', views.activate, name='activate'),
	path('profile/', views.profile, name='profile'),
	path('profile/update_image/', views.update_image, name='update_image'),
	path('profile/edit/', views.edit_profile, name='edit_profile'),
	path('profile/change_password/', views.change_password, name='change_password'),
	path('goals/', views.goals, name='goals'),
	path('checkin_goals/', views.checkin_goals, name='checkin_goals'),
	path('goal/<int:goal_id>', views.checkin_from_goals_custom, name='checkin_custom_goal'),
	path('create_goal/', views.create_basic_goal, name='create_goal'),
	path('create_custom_goal/', views.create_custom_goal, name='create_custom_goal'),
	path('update_goals/', views.update_goals, name='update_goals'),
	path('exercise/', views.exercise, name='exercise'),
	path('exercise/add_new_exercise',views.add_new_exercise,name='add_new_exercise'),
	path('exercise/add_daily_note', views.add_daily_note, name='add_daily_note'),
	path('exercise/add_daily_exercise',views.add_daily_exercise,name='add_daily_exercise'),
	path('exercise/search_exercise',views.search_exercise_dictionary,name='search_exercise'),
	path('exercise/get_calorific_exercise_info',views.get_calorific_exercise_info,name='get_calorific_exercise_info'),
	path('exercise/update',views.update_exercise,name='update_exercise'),

	path('diet/', views.diet, name='diet'),
	path('diet/add_new_food',views.add_new_food,name='add_new_food'),
	path('diet/add_today_diet', views.add_today_diet, name='add_today_diet'),
	path('diet/search/', views.search_food_dictionary,name='search'),
	path('diet/get_calorific_info/',views.get_calorific_info,name='get_calorific_info'),
	path('diet/update/', views.update_diet, name = 'update_diet'),


	#
	# path('groups/', views.groups, name='groups'),
	# path('groups/group_page/', views.group_page, name='group_page'),
	# path('groups/group_page/<int:group_id>', views.group_page, name='group_page'),
	path('groups/', views.my_group, name='groups'),
	path('update_groups/', views.update_groups, name='update_groups'),
	path('groups/group_page/<int:group_id>/', views.group_page, name='group_page'),
	path('groups/group_page/<int:group_id>/create_post/', views.create_post, name='create_post'),
	path('groups/group_page/<int:group_id>/create_comment/<int:post_id>/', views.create_comment, name='create_comment'),
	path('groups/group_page/<int:group_id>/delete_group/', views.delete_group, name='delete_group'),
	path('groups/group_page/<int:group_id>/leave_group/', views.leave_group, name='leave_group'),
	path('groups/search_group/', views.search_group, name='search_group'),
	path('groups/create_group/', views.create_group, name='create_group'),
	path('groups/join_group/', views.join_group, name='join_group'),
	path('groups/group_page/<int:group_id>/members/', views.members, name='members'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)