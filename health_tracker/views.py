import decimal
from functools import wraps
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.validators import validate_email
from django.db import IntegrityError
from django.db.models import Sum, Count, Value, IntegerField, F, Q
from django.utils.encoding import force_text, force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from .models import *
from datetime import date, datetime
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import render
from health_tracker.models import Post, FoodDictionary


def response(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        try:
            message = view(*args, **kwargs)
            return HttpResponse(message)
        except PermissionDenied as e:
            print(e)
            return HttpResponseForbidden(e)
        except ValidationError as e:
            print(e.message)
            return HttpResponseBadRequest(e.message)
        except IntegrityError as e:
            print(e)
            return HttpResponseBadRequest(e)
        except Exception as e:
            print(e)
            return HttpResponseBadRequest('unknown error')
    return wrapper

@login_required(redirect_field_name=None)
@require_http_methods(["GET", "POST"])
def home(request):
    user = request.user
    caloric_intake = UserFood.objects.filter(user_id=user.id).filter(
        date_intake=datetime.today().strftime('%Y-%m-%d')).aggregate(Sum('calorie_eaten_per_food'))
    calorie_intake = caloric_intake.get('calorie_eaten_per_food__sum') or 0

    calories_burnt=UserExercise.objects.filter(user_id=user.id)\
                                      .filter(activity_date=datetime.today().strftime('%Y-%m-%d'))\
                                      .aggregate(Sum('calories_burnt'))
    calories_burnt = calories_burnt.get('calories_burnt__sum') or 0


    data = [60, 60, 50.9, 50.8, 43]
    data_label = None if data is None else list(range(1, len(data)+1))
    goals_to_check = UserCustomGoal.objects.filter(user_id=user.id, goal_id__is_met=False).all()
    # Check if any of the goals have expired.
    for goal in goals_to_check:
        if goal.goal_id.date.strftime('%Y-%m-%d') < date.today().strftime('%Y-%m-%d'):
            complete_custom_goal(user, goal.goal_id)
    if BasicGoalProgress.objects.filter(user_id=user.id, date=date.today().strftime('%Y-%m-%d')).exists():
        weight = None
    else:
        weight = UserProfile.objects.get(user=user).weight
    recent_goals = UserCustomGoal.objects.annotate(progress=Count('customgoalprogress'),
                                                   total_progress=F('goal_id__act_frequency') * F('goal_id__pass_interval'),
                                                   percentage=F('progress') * 100 / F('total_progress')).filter(user_id=user.id)
    suggest_goal = None
    if recent_goals:
        recent_goals = recent_goals.filter(goal_id__is_met=False).order_by('-goal_id__start_date').all()[:3]
        suggest_goal = {'goal_description': 'do sit-up everyday',
                        'date': '2020-12-31',
                        'days': 1,
                        'period': 1,
                        'metric': 'days'
                        }

    context = {
        'weight': weight,
        'goals_to_check': goals_to_check,
        'suggest_goal': suggest_goal,
        'calorie_intake': calorie_intake,
        'calories_burnt': calories_burnt,
        'net_calorie': calorie_intake - calories_burnt,
        'calorie_goal_progress': 50,
        'recent_goals': recent_goals,
        'data': data,
        'data_label': data_label
    }
    return render(request, 'home.html', context)

@login_required(redirect_field_name=None)
@require_http_methods(["GET", "POST"])
def profile(request):
    user = request.user
    data = UserProfile.objects.get(user=user)
    info = {
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'gender': data.gender,
        'date_of_birth': data.date_of_birth.strftime('%Y-%m-%d'),
        'height': data.height,
        'weight': data.weight,
        'waist_circumference': data.waist_circumference,
        'profile_picture': data.profile_picture,
    }
    return render(request, 'profile.html', info)

@require_POST
@response
def update_image(request):
    user = request.user
    data = UserProfile.objects.get(user=user)
    image = request.FILES['image']
    data.profile_picture = image
    data.save()
    return 'successfully updated profile image'

@require_POST
@response
def edit_profile(request):
    user = request.user
    data = UserProfile.objects.get(user=user)
    input_data = request.POST

    if input_data['username'] != user.username:
        user.username = input_data['username']
    if input_data['first_name'] != user.first_name:
        user.first_name = input_data['first_name']
    if input_data['last_name'] != user.last_name:
        user.last_name = input_data['last_name']
    if input_data['email'] != user.email and validate_email(input_data['email']):
        user.email = input_data['email']
    if input_data['gender'] != data.gender:
        data.gender = input_data['gender']
    if input_data['date_of_birth'] != data.date_of_birth:
        data.date_of_birth = input_data['date_of_birth']
    if input_data['height'] != data.height:
        data.height = input_data['height']
    if input_data['weight'] != data.weight:
        data.weight = input_data['weight']
    if input_data['waist_circumference'] != data.waist_circumference:
        data.waist_circumference = input_data['waist_circumference']

    user.save()
    data.save()
    return "profile updated"

@require_POST
@response
def change_password(request):
    user = request.user
    current_password = request.POST['current']
    new_password = request.POST['new']
    repeat_password = request.POST['repeat']

    if new_password != repeat_password:
        raise ValidationError('password does not match')
    validate_password(new_password)
    user = authenticate(request, username=user.username, password=current_password)
    if user is None:
        raise PermissionDenied('password is incorrect, action aborted')
    time_now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")

    send_mail(
        'Health Tracker: Password change confirmation',
        f'''\
        Hi {user},\n

        We are writing this email to notify you that your password of your account has been changed at {time_now},
        you can now log in with your new password.
        If you did not change your password, Please contact us to recover your account.\n

        Health Tracker team
        ''',
        settings.EMAIL_HOST_USER,
        [user.email]
    )
    user.set_password(new_password)
    user.save()
    return 'password changed successfully'

@login_required(redirect_field_name=None)
@require_http_methods(["GET", "POST"])
def goals(request):
    from .models import UserCustomGoal

    user = request.user
    goals = UserCustomGoal.objects.annotate(progress=Count('customgoalprogress'),
                                            total_progress=F('goal_id__act_frequency')*F('goal_id__pass_interval'),
                                            percentage=F('progress')*100/F('total_progress')).filter(user_id=user.id)
    past_goals = None
    if goals:
        goals = goals.filter(goal_id__is_met=False).order_by('-goal_id__start_date').all()
        past_goals = goals.filter(goal_id__is_met=True).order_by('-goal_id__start_date').all()

    return render(request, 'goals.html', {'goals': goals, 'past_goals': past_goals})

def update_goals(request):
    user = request.user
    goals = UserCustomGoal.objects.annotate(progress=Count('customgoalprogress'),
                                            total_progress=F('goal_id__act_frequency') * F('goal_id__pass_interval'),
                                            percentage=F('progress') * 100 / F('total_progress')).filter(user_id=user.id)
    if goals:
        goals = goals.filter(goal_id__is_met=False).order_by('-goal_id__start_date').all()

    return render(request, 'goals_display.html', {'goals': goals})


def checkin_goals(request):
    user = request.user
    updated = request.POST.get('basic-goal-update')
    if updated:
        create_basic_goal_progress(user, updated)

    archived_goals = request.POST.getlist('is-goal-checked')
    if archived_goals:
        for goal_id in archived_goals:
            create_custom_goal_progress(user, goal_id)

    return HttpResponse(200)

@response
def create_basic_goal(request):
    # get data from the form
    user = request.user
    target = request.POST['target']
    metric = request.POST['metric']
    complete_date = request.POST['basic_goal_complete_date']
    print(target, metric, complete_date)
    # create a basic goal for the user
    from datetime import date
    from .models import BasicGoal

    goal = None
    if BasicGoal.objects.exists():
        goal = BasicGoal.objects.filter(user_id=user.id).first()
    if goal:
        raise ValidationError("You may only have one basic goal at a time.")
    if UserProfile.objects.get(id=user.id).waist_circumference == target:
        raise ValidationError("Cannot set goal as current weight/waist circumference.")
    # Basic date check
    if datetime.strptime(complete_date, '%Y-%m-%d').date() < date.today():
        raise ValidationError("End date cannot be before today.")
    BasicGoal.objects.create(user_id=user, is_met=False, target_weight=target, metric=metric, date=complete_date)

    return "basic goal created successfully"


def create_basic_goal_progress(user, current, metric='Weight'):
    from datetime import date
    from .models import BasicGoalProgress

    today = date.today().strftime('%Y-%m-%d')

    record = {'waist_circumference': current} if metric == 'WaistCircumference' else {'weight': current}
    progress = {'user_id': user, 'date': today}

    progress.update(record)
    UserProfile.objects.update(**record)
    return BasicGoalProgress.objects.create(**progress)


def complete_custom_goal(user, goal_id):
    goal = UserCustomGoal.objects.filter(user_id=user.id, goal_id=goal_id).first()
    goal.is_met = True

    return 'goal is completed'


@response
def create_custom_goal(request, group_id=None):
    user = request.user
    goal_description = request.POST['goal_description']
    days = int(request.POST['days'])
    period = int(request.POST['period'])
    period_metric = request.POST['period_metric']
    complete_date = request.POST['custom_goal_complete_date']

    from datetime import date
    from .models import CustomGoal, UserCustomGoal

    if period_metric == 'weeks':
        period = period * 7
    elif period_metric == 'months':
        period = period * 30

    # Can't complete goal for more days than exist in the time period
    if period < days:
        raise ValidationError("Can't complete goal for more days than exist in the time period")
    # Basic date check
    if datetime.strptime(complete_date, '%Y-%m-%d').date() < date.today():
        raise ValidationError("Please enter a day after today")   ### fill in error message
    # If the length of the goal is less than the period (e.g. cant go to the gym every day for a month in a week period)
    if (datetime.strptime(complete_date, '%Y-%m-%d').date() - date.today()).days < period:
        raise ValidationError("Length of the goal cannot be less than the period")

    periods_in_duration = int((datetime.strptime(complete_date, '%Y-%m-%d').date() - date.today()).days/period)

    # create the customgoal
    created_custom_goal = CustomGoal.objects.create(goal_description=goal_description, start_date=date.today().strftime('%Y-%m-%d'),
                                                    date=complete_date,
                                                    is_met=False, checkin_interval=period, group_id=group_id,
                                                    act_frequency=days, act_period_length=period, pass_interval=periods_in_duration)

    UserCustomGoal.objects.create(user_id=user, goal_id=created_custom_goal)
    return "custom goal created successfully"


@response
def create_custom_goal_progress(user, goal):
    today = date.today().strftime('%Y-%m-%d')
    goal = UserCustomGoal.objects.filter(user_id=user.id, goal_id=goal).first()
    customgoal = CustomGoalProgress.objects.filter(user_custom_goal=goal, date=today)
    if customgoal:
        raise ValidationError("Cannot check in twice a day.")
    else:
        CustomGoalProgress.objects.create(user_custom_goal=goal, date=today)


def checkin_from_goals_custom(request, goal_id):
    user = request.user

    create_custom_goal_progress(user, goal_id)

    return goals(request)

@login_required(redirect_field_name=None)
@require_http_methods(["GET", "POST"])
def exercise(request):
    user_id=request.user.id
    user_exercise = UserExercise()
    daily_exercise = user_exercise.daily_exercise(user_id)#fetch daily exercises for that user

    note_obj=DailyUserExerciseNotes()
    note_value=note_obj.daily_note(user_id=user_id) or ''#fetch daily exercise note for that user

    context = \
        {
            'daily_exercise': daily_exercise,
            'note_value':note_value
        }
    return render(request, 'exercise.html', context)


@response
def add_new_exercise(request):
    if request.method == 'POST':
        exercise_name = request.POST.get('name')
        met_value = int(request.POST.get('met_value'))
        if exercise_name == '':
            raise ValidationError("Please specify an exercise name")
        elif met_value <= 0:
            raise ValidationError("Please enter a valid met value")
        if ExerciseDictionary.objects.filter(specific_motion=exercise_name).exists():
            raise IntegrityError("Food or drink already exists in database")
        fd = ExerciseDictionary()  # Java like code. Instantiate class first
        fd.save_new_exercise(exercise_name=exercise_name, met_value=met_value)
    return "Exercise added successfully"

@response
def add_daily_note(request):
    if request.method=='POST':
        daily_note=request.POST.get('note')
        daily_note_obj=DailyUserExerciseNotes()
        daily_note_obj.add_or_update_daily_note(request.user,daily_note)
    return "Daily note recorded"
@response
def add_daily_exercise(request):
    if request.method == 'POST':
        exercise=request.POST.get('exercise')
        if exercise=='':
            raise ValidationError('Exercise name cannot be blank')
        if request.POST.get('duration')=='':
            raise ValidationError('duration field is empty')
        duration=int(request.POST.get('duration'))
        if duration<=0:
            raise ValidationError('Duration cannot be less or equal to 0')
        if request.POST.get('calories')=='':
            raise ValidationError('calories field is empty')
        calories=float(request.POST.get('calories'))
        if calories<=0:
            raise ValidationError('Duration cannot be less or equal to 0')
        if exercise and duration and calories and calories:
            exercise_obj = ExerciseDictionary.objects.get(specific_motion=exercise)
            UserExercise.objects.create(user_id=request.user,duration=duration,exercise_id=exercise_obj, calories_burnt=calories, activity_date=datetime.today())
    return "Daily exercise added successfully"

def search_exercise_dictionary(request):
    if request.is_ajax():
        # search database with search term
        exercise_data = ExerciseDictionary.objects \
            .filter(specific_motion__contains=request.GET.get('search', None)) \
            .values(label=F('specific_motion'), value=F('met_value'), amount=Value(60, IntegerField()))
        return JsonResponse(list(exercise_data), safe=False)

def get_calorific_exercise_info(request):
    if request.is_ajax():
        exercise = ExerciseDictionary.objects.get(specific_motion=request.GET.get('name', None)) # get specific exercise from database
        weight=UserProfile.objects.get(user_id=request.user).weight
        calorie_for_exercise = round(exercise.met_value * 3.5 * float((weight/200)) *int(request.GET.get('duration')), 2)  # METs x 3.5 x (your body weight in kilograms) / 200 = calories burned per minute.
        print(calorie_for_exercise)
        return JsonResponse({'calorie_for_exercise': calorie_for_exercise})


@login_required(redirect_field_name=None)
@require_http_methods(["GET", "POST"])
def diet(request):
    water_intake = int(request.POST.get('water_intake', 0))
    print(water_intake)

    water_in = DailyWaterIntake()
    user_food = UserFood()
    if request.method == 'POST':

        if water_intake:
            water_in.add_or_update_water_intake(user_id=request.user.id, water_intake=water_intake)

    daily_intake = user_food.daily_food_intake(request.user.id)

    water_intake = water_in.daily_water_intake(request.user.id)

    key = min(water_intake, 18)
    switch = {
        0: 'emptyGlass.JPG',
        range(1, 4): 'minimumFill.JPG',
        range(4, 7): 'afterMinimum1.JPG',
        7: 'minimumFill1.JPG',
        8: 'minimumFill2.JPG',
        9: 'minimumFill3.JPG',
        10: 'minimumFill4.JPG',
        11: 'minimumFill5.JPG',
        range(12, 14): 'minimumFill6.JPG',
        range(14, 18): 'minimumFill7.JPG',
        18: 'maxFill.JPG'
    }

    image_path = "img/water_intake_glasses/"
    for water_level, image in switch.items():
        if key == water_level:
            image_path += image
            break
        elif not isinstance(water_level, int):
            if key in water_level:
                image_path += image
                break


    print(water_intake)
    context = \
        {
            'water_intake': water_intake,
            'daily_intake': daily_intake,
            'image_path': image_path,
        }
    return render(request, 'diet.html', context)


@response
def add_new_food(request):
    if request.method == 'POST':
        food_name = request.POST.get('food_name')  # adding a food to FoodDictionary
        calories_per_100g = int(request.POST.get('calories_per_100g'))  # adding to FoodDictionary
        if food_name == '':
            raise ValidationError("Please specify a food or drink name")
        elif calories_per_100g <= 0:
            raise ValidationError("Please enter a valid base calorific value")
        if FoodDictionary.objects.filter(food_name=food_name).exists():
            raise IntegrityError("Food or drink already exists in database")
        fd = FoodDictionary()  # Java like code. Instantiate class first
        fd.save_new_food(food_name=food_name, calories=calories_per_100g)
    return "Food or drink added successfully"


@response
def add_today_diet(request):
    food_drink_name = request.POST.get('food_drink_name')  # adding a user meal
    if food_drink_name == '':
        raise ValidationError("Please specify a food or drink name")
    meal_category = request.POST.get('meal_category')
    calories = int(request.POST.get('calories'))  # adding a user meal
    if calories <=0:
        raise ValidationError("Please enter a valid calorific value")
    portion=int(request.POST.get('portion'))
    if portion<=0:
        raise ValidationError("Please enter a valid portion size")

    user_food = UserFood()
    if request.method == 'POST':
        if meal_category and food_drink_name and calories and portion:
            intake = user_food.save_daily_food_intake(request.user, food_drink_name, meal_category, portion, calories)
    return 'Meal successfully added'



def search_food_dictionary(request):
    if request.is_ajax():
        # search database with search term
        food_data = FoodDictionary.objects \
            .filter(food_name__contains=request.GET.get('search', None)) \
            .values(label=F('food_name'), value=F('calories'), amount=Value(100, IntegerField()))

        return JsonResponse(list(food_data),safe=False)

def get_calorific_info(request):
    if request.is_ajax():
        food = FoodDictionary.objects.get(food_name=request.GET.get('name', None))
        calorie_per_portion = round((food.calories) * (int(request.GET.get('portion')) / 100),2)
        print(calorie_per_portion)
        return JsonResponse({'calorie_per_portion': calorie_per_portion})

@login_required(redirect_field_name=None)
@require_http_methods(["GET", "POST"])
def my_group(request):
    belongs = Group.objects.filter(usergroup__user_id=request.user).all()
    infos = CustomGoal.objects.all()

    context = {
            'belongs': belongs,  # this should be changed depending on user logged in
            'infos': infos
        }
    return render(request, 'groups.html', {'belongs': belongs, 'infos': infos})

def update_groups(request):
    belongs = Group.objects.filter(usergroup__user_id=request.user).all()
    infos = CustomGoal.objects.all()

    context = {
        'belongs': belongs,  # this should be changed depending on user logged in
        'infos': infos
    }
    return render(request, 'groups_display.html', {'belongs': belongs, 'infos': infos})


@require_POST
def login(request):
    username = request.POST['login_username']
    password = request.POST['login_password']
    user = authenticate(request, username=username, password=password)
    if user is None:
        return HttpResponseForbidden("Invalid username or password")
    elif not user.is_active:
        return HttpResponseForbidden("User is not activated yet, please verify your account email")

    auth_login(request, user)
    return HttpResponseRedirect('/home/')

@csrf_exempt
@require_POST
def username_exists(request):
    if User.objects.filter(username=request.POST['username']).exists():
        return HttpResponseForbidden('username already exists')
    else:
        return HttpResponse('')

@require_POST
@response
def create_user(request):
    first_name = request.POST['first_name']
    last_name = request.POST['last_name']
    username = request.POST['username']
    email = request.POST['email']
    height = float(request.POST['height'])
    weight = float(request.POST['weight'])
    gender = request.POST['gender']
    waist_circumference = float(request.POST['waist']) if request.POST['waist'] != '' else None
    date_of_birth = request.POST['dob']
    password = request.POST['password']
    password_repeat = request.POST['password_repeat']

    # validation on different fields
    if password != password_repeat:
        raise ValidationError('Please ensure the password repeat is matched')
    validate_password(password)
    validate_email(email)
    if not '1900-01-01' <= date_of_birth <= '2010-12-31':
        raise ValidationError('Invalid date of birth')
    if height not in range(130, 281):
        raise ValidationError('height must be between 130 and 280')
    if weight not in range(30, 636):
        raise ValidationError('weight must be between 30 and 635')
    bound = {'Male': range(70, 131), 'Female': range(65, 116), 'Prefer_not_to_say': range(65, 131)}[gender]
    if waist_circumference is not None and waist_circumference not in bound:
        raise ValidationError(f'waist circumference must be between {bound.start} and {bound.stop}')

    # creating user on the database
    new_user = User.objects.create_user(username, email, password,
                                        first_name=first_name, last_name=last_name, is_active=False)
    UserProfile.objects.create(user=new_user, date_of_birth=date_of_birth,
                               gender=gender, height=height, weight=weight,
                               waist_circumference=waist_circumference,
                               profile_picture='profile_image/default.png')

    # send out the verification email
    domain = get_current_site(request).domain
    uid = urlsafe_base64_encode(force_bytes(new_user.id))
    token = account_activation_token.make_token(new_user)
    send_mail(
        'Health Tracker: Verification required',
        f'''
        Thank you for registering. 
        Please click the link below to verify account
        http://{domain}/activate/{uid}/{token}
        ''',
        settings.EMAIL_HOST_USER,
        [email]
    )

    return 'Account created successfully. Please check your email to activate your account.'

class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        from six import text_type
        return (
            text_type(user.pk) + text_type(timestamp) +
            text_type(user.is_active)
        )

account_activation_token = AccountActivationTokenGenerator()

def activate(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(id=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        return HttpResponse('Thank you for your email confirmation. Now you can login your account.')
    elif user.is_active:
        return HttpResponse('Account has already been activated')
    else:
        return HttpResponse('Activation link is invalid!')

def group_page(request,group_id=None):
    user = request.user
    profile_picture = UserProfile.objects.get(user=user).profile_picture
    group_info = CustomGoal.objects.get(group_id=group_id)
    get_name = Group.objects.get(id=group_id).name

    from .models import Post
    posts = Post.objects.filter(group_id=group_id).all()
    comments = Comment.objects.all()
    users = User.objects.filter(usergroup__group_id=group_id).all()
    admin = Usergroup.objects.get(group_id=group_id, is_admin=True)
    username = user.username
    is_admin = admin.user_id.username
    context = {
        'me': user,
        'users': users,
        'is_admin': is_admin,
        'group_id': group_id,
        'profile_picture': profile_picture,
        'group_info': group_info,
        'posts': posts,
        'get_name': get_name,
        'comments': comments
    }
    return render(request, 'group_page.html', context)


@response
def create_group(request):
    user = request.user
    group_name = request.POST['group_name']

    from .models import Groups, Usergroup
    new_group = Group.objects.create(name=group_name)
    Groups.objects.create(group=new_group, group_type='OPEN')
    create_custom_goal(request, new_group.id)
    Usergroup.objects.create(is_admin=True, group_id=new_group, user_id=user)
    return "group created successfully"


def search_group(request):
    if request.is_ajax():

        groups_data = Group.objects \
            .filter(name__contains=request.GET.get('search_group', None)).values(label=F('name'))
        print(groups_data)
        return JsonResponse(list(groups_data), safe=False)

@response
def join_group(request):
    user = request.user
    group_name = request.POST['group_name']
    from .models import Usergroup, UserCustomGoal
    this_group = Group.objects.get(name=group_name)
    # get_group = Groups.objects.get(group_id=this_group)
    Usergroup.objects.create(user_id=user, is_admin=False, group_id=this_group)
    get_goal_id = CustomGoal.objects.get(group_id=this_group.id)
    UserCustomGoal.objects.create(user_id=user, goal_id=get_goal_id)
    return "joined group successfully"


def create_post(request, group_id):
    user = request.user
    content = request.POST['content']
    from .models import Post, Comment
    Post.objects.create(content=content, user=user, group_id=group_id)
    posts = Post.objects.filter(group_id=group_id).all()
    render(request, 'group_page.html', {'group_id': group_id, 'posts': posts})
    return group_page(request, group_id)

def create_comment(request,group_id, post_id):
    user = request.user
    comment = request.POST.get('add_comment')
    # print('is this comment none?',comment)
    from .models import Comment
    Comment.objects.create(user=user, comment=comment, post_id=post_id)
    render(request, 'group_page.html', {'group_id': group_id, 'post_id': post_id})
    return group_page(request, group_id)

def delete_group(request, group_id):
    Group.objects.get(id=group_id).delete()
    delete = CustomGoal.objects.get(group_id=group_id)
    # Usergroup.objects.get(group_id=group_id).delete()
    Post.objects.filter(group_id=group_id).all().delete()
    CustomGoal.objects.get(group_id=group_id).delete()
    UserCustomGoal.objects.filter(goal_id=delete.goal_id).all().delete()
    render(request, "groups.html")
    return my_group(request)

def leave_group(request, group_id):
    user = request.user
    delete = CustomGoal.objects.get(group_id=group_id)
    Usergroup.objects.get(user_id=user, group_id=group_id).delete()
    UserCustomGoal.objects.get(user_id=user, goal_id=delete.goal_id).delete()
    render(request, "groups.html")
    return my_group(request)

def members(request, group_id):
    # user = request.user
    users = User.objects.filter(usergroup__group_id=group_id).all()
    admin = Usergroup.objects.get(group_id=group_id, is_admin=True)
    is_admin = admin.user_id


    goals = UserCustomGoal.objects.annotate(progress=Count('customgoalprogress'),
                                            total_progress=F('goal_id__act_frequency') * F('goal_id__pass_interval'),
                                            percentage=F('progress') * 100 / F('total_progress'))
    # .filter(user_id=user.id)
    custom = CustomGoal.objects.filter(group_id=group_id).first()
    custom_goal_id = custom.goal_id

    if goals:
        goals = goals.filter(goal_id__is_met=False).order_by('-goal_id__start_date').all()

    context = {
        'group_id': group_id,
        'users': users,
        'is_admin': is_admin,
        'goals': goals,
        'custom_goal_id': custom_goal_id
    }
    return render(request, 'group_member_list.html', context)


def update_diet(request):
    user_food = UserFood()
    daily_intake = user_food.daily_food_intake(request.user.id)
    context={'daily_intake':daily_intake}

    return render(request,'diet_display_food.html', context)


def update_exercise(request):
    user_exercise = UserExercise()
    daily_exercise = user_exercise.daily_exercise(request.user.id)
    context={'daily_exercise':daily_exercise}

    return render(request,'exercise_display_table.html',context)