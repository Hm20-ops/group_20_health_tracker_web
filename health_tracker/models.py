from datetime import datetime

from django.core.mail import send_mail
from django.db import models
from django.contrib.auth.models import User, Group
from django.template.loader import get_template

from django.conf import settings


class UserProfile(models.Model):
    class Gender(models.TextChoices):
        MALE = ('Male')
        FEMALE = ('Female')
        Other = ('Prefer Not To Say')
    # all measurements are in cm
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_of_birth = models.DateField(blank=False, null=False)
    height = models.DecimalField(blank=False, null=False, max_digits=4, decimal_places=1)  # counting in cm->163.2cm
    weight = models.DecimalField(blank=False, null=False, max_digits=4, decimal_places=1)
    waist_circumference = models.DecimalField(blank=True, null=True, decimal_places=1,
                                              max_digits=4)  # on needed basis for people who choose this option
    profile_picture = models.ImageField(upload_to='profile_image',
                                        blank=True)  # profile_image is a folder on disk for static image files
    gender = models.TextField(choices=Gender.choices, default=Gender.Other,null=False,blank=False)
    #gender = models.TextField(blank=False, choices=Gender.choices,default=Gender.Male)




    class Meta:
        managed = True  # reflected in the database
        verbose_name_plural='user_profiles'
        db_table = 'user_profile'  # obeys djangos conventions of naming table


class FoodDictionary(models.Model):  # django underscores two different word. First letter is lowercase
    food_id = models.AutoField(db_column='food_id', primary_key=True)  # Field name made lowercase.
    food_name = models.CharField(max_length=150, db_column='food_name', blank=True,
                                 null=False,unique=True)  # Field name made lowercase.
    calories = models.FloatField(blank=False, null=False)
    '''
    UserFood is an intermediary table
    Without abstraction of the ORM, we essentially have 3 related tables
    i.e. FoodDictionary, 
    AUTH_USER_MODEL, UserFood
    '''
    UserFood = models.ManyToManyField(
        User, through='UserFood')  # links to userId through foodConsumed table

    def __str__(self):
        return self.food_name

    def save_new_food(self,food_name,calories):
        self.food_name=food_name
        self.calories=calories
        self.save()

    class Meta:
        managed = True  # reflected in the database
        db_table = 'food_dictionary'  # obeys djangos conventions of naming table
        constraints = [
            models.CheckConstraint(
                check=models.Q(
                    calories__gt=0  # Translates to calorie_eaten_per_food>=0
                    # see https://docs.djangoproject.com/en/2.2/ref/models/constraints/#django.db.models.CheckConstraint
                ),
                name="calories_per_food_constraint",
            )
        ]
        verbose_name_plural='food_dictionary'



class UserFood(models.Model):
    MealType = models.TextChoices('MealType', 'Breakfast Lunch Dinner')
    consumption_id = models.AutoField(primary_key=True,
                                      db_column='consumption_id')  # autofield means field is autogenerated
    user_id = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column='user_id')  # if user is deleted from database, delete the row
    food_id = models.ForeignKey(FoodDictionary, on_delete=models.CASCADE,
                                db_column='food_id')  # if user wrongly enters a food, user can delete the row
    calorie_eaten_per_food = models.FloatField(blank=False, null=False)
    # formats date in dd/mm/yyyy and automatically timestamps when a food is added.
    # #Cannot override timestamp
    date_intake = models.DateField(auto_now_add=True, auto_now=False,
                                   null=False)  # automatically timestamps when intake is specificied
    meal_category = models.TextField(blank=False, choices=MealType.choices)

    food_amount=models.IntegerField(blank=False,null=False)

    def __str__(self):
        return """user with userId {} ate food with foodId {} containing {} calories on {}""".format(self.user_id,
                                                                                                     self.food_id,
                                                                                                     self.calorie_eaten_per_food,
                                                                                                     self.date_intake)
    def daily_food_intake(self,user_id):
        daily_intake = UserFood.objects.filter(user_id=user_id).filter(date_intake=datetime.today()).all()
        return daily_intake

    def save_daily_food_intake(self,user,food_drink_name,meal_category,portion,calories):

        food_obj=FoodDictionary.objects.get(food_name=food_drink_name)
        user_food= UserFood(user_id=user, food_id=food_obj,calorie_eaten_per_food=calories,food_amount=portion,meal_category=meal_category)
        user_food.save()
        return user_food

    class Meta:
        managed = True
        unique_together = ('meal_category', 'user_id', 'food_id', 'date_intake')
        db_table = 'user_food'  # obeys djangos conventions of naming table
        constraints = [
            models.CheckConstraint(
                check=models.Q(
                    calorie_eaten_per_food__gte=0  # Translates to calorie_eaten_per_food>=0
                    # see https://docs.djangoproject.com/en/2.2/ref/models/constraints/#django.db.models.CheckConstraint
                ),
                name="calorie_eaten_per_food_constraint",
            )
        ]
        verbose_name_plural='user_foods'

class ExerciseDictionary(models.Model):
    exercise_id = models.AutoField(primary_key=True, db_column='exercise_id')  # Field name made lowercase.
    activity = models.CharField(max_length=150, blank=True, null=True)
    specific_motion = models.CharField(max_length=150, db_column='specific_motion', blank=True,
                                       null=True)  # Field name made lowercase.
    met_value = models.FloatField(db_column='met_value', blank=True, null=True)  # Field name made lowercase.

    UserExercise= models.ManyToManyField(
        User, through='UserExercise')  # links to userId through foodConsumed table

    def save_new_exercise(self,exercise_name,met_value):
        self.specific_motion=exercise_name
        self.met_value=met_value
        self.save()

    def __str__(self):
        return self.specific_motion

    class Meta:
        managed = True
        verbose_name_plural='exercise_dictionary'
        db_table = 'exercise_dictionary'


class UserExercise(models.Model):
    activity_id = models.AutoField(db_column='activity_id', primary_key=True, blank=True)  # Field name made lowercase.
    # exercise_id = models.IntegerField(db_column='exercise_id', blank=True, null=True)  # Field name made lowercase.
    calories_burnt = models.FloatField(db_column='calories_burnt')  # Field name made lowercase.
    activity_date = models.DateField(auto_now_add=True, auto_now=False, db_column='activity_date', blank=True,
                                     null=True)  # Field name made lowercase.
    duration=models.IntegerField(db_column='duration',null=True,blank=True)

    user_id = models.ForeignKey(
        User, on_delete=models.CASCADE,null=False, db_column='user_id')  # if user is deleted from database, delete the row

    exercise_id = models.ForeignKey(ExerciseDictionary,null=False,on_delete=models.CASCADE,db_column='exercise_id')

    def daily_exercise(self,user_id):
        daily_exercise = UserExercise.objects.filter(user_id=user_id).filter(activity_date=datetime.today()).all().values('exercise_id__specific_motion','duration','calories_burnt')
        print(daily_exercise)
        return daily_exercise

    class Meta:
        managed = True
        verbose_name_plural='user_exercises'
        db_table = 'user_exercise'

class DailyUserExerciseNotes(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, null=False, db_column='user_id')
    note_date = models.DateField(auto_now_add=True, auto_now=False, db_column='activity_date', blank=True,null=True)  # Field name made lowercase.
    note_value=models.TextField(blank=True,null=False,name='note_value')

    def add_or_update_daily_note(self, user_id, daily_note):
        DailyUserExerciseNotes.objects.update_or_create\
        (
            # if data for this user already exists in database, update it. Otherwise, create new entry
            user_id=user_id, note_date=datetime.today(),
            defaults={'note_value': daily_note},  # dictionary for either update or create
        )
    def daily_note(self,user_id):
        note_obj = DailyUserExerciseNotes.objects.filter(user_id=user_id, note_date=datetime.today()).first()
        return 0 if note_obj is None else note_obj.note_value

    class Meta:
        managed = True
        db_table = 'daily_user_exercise_notes'

class BasicGoal(models.Model):
    Metric = models.TextChoices('Metric', 'Weight WaistCircumference')
    user_id = models.OneToOneField(User, on_delete=models.CASCADE, db_column='user_id', blank=False, null=False)
    target_weight = models.FloatField(blank=False, null=False)
    date = models.DateField()
    is_met = models.BooleanField(db_column='is_met')  # Field name made lowercase.
    metric = models.TextField(blank=False, choices=Metric.choices, null=False)

    class Meta:
        managed = True
        db_table = 'basic_goal'
        verbose_name_plural='basic_goal'


class BasicGoalProgress(models.Model):
    basic_goal_progress_id = models.AutoField(primary_key=True)  # django does not support composite primary key
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id', blank=True, null=True)
    date = models.DateField(blank=False, null=True)  # do we want this to be null?
    weight = models.FloatField(blank=False, null=False)

    class Meta:
        managed = True
        unique_together = (
        'user_id', 'date')  # unique constraint on user_id and date as Django does not support composite primary key
        db_table = 'basic_goal_progress'
        verbose_name_plural='basic_goal_progress'
        constraints = [
            models.CheckConstraint(
                check=models.Q(
                    weight__gte=0  # Translates to calorie_eaten_per_food>=0
                    # see https://docs.djangoproject.com/en/2.2/ref/models/constraints/#django.db.models.CheckConstraint
                ),
                name="weight_constraint",
            )
        ]


class CustomGoal(models.Model):
    goal_id = models.AutoField(primary_key=True)
    goal_description = models.TextField()
    start_date = models.DateField()
    date = models.DateField()
    is_met = models.BooleanField(db_column='is_met')  # Field name made lowercase.
    checkin_interval = models.IntegerField()
    act_frequency = models.IntegerField()
    act_period_length = models.IntegerField()
    pass_interval = models.IntegerField()
    group_id = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'custom_goal'
        verbose_name_plural='custom_goal'


class UserCustomGoal(models.Model):
    user_custom_goal = models.AutoField(primary_key=True)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id')
    goal_id = models.ForeignKey(CustomGoal, on_delete=models.CASCADE, db_column='goal_id')

    class Meta:
        verbose_name_plural='user_custom_goals'
        unique_together = ('user_id', 'goal_id')
        managed = True
        db_table = 'user_custom_goal'


class CustomGoalProgress(models.Model):
    custom_goal_progress = models.AutoField(primary_key=True)
    user_custom_goal = models.ForeignKey(UserCustomGoal, on_delete=models.CASCADE, db_column='user_custom_goal')
    date = models.DateField(blank=False, null=True)

    class Meta:
        verbose_name_plural='custom_goal_progress'
        unique_together = ('user_custom_goal', 'date')
        managed = True
        db_table = 'custom_goal_progress'


class Groups(models.Model):
    group = models.OneToOneField(Group, on_delete=models.CASCADE)
    Type = models.TextChoices('Type', 'OPEN CLOSED')
    group_type = models.TextField(blank=False, choices=Type.choices, null=False)
    group_description=models.TextField(blank=True,null=False)

    # group_name = models.TextField(db_column='group_name')  # Field name made lowercase. This field type is a guess.

    class Meta:
        managed = True
        db_table = 'groups'
        verbose_name_plural='groups'


class Usergroup(models.Model):
    user_id = models.ForeignKey(User,db_column='user_id', on_delete=models.CASCADE)
    group_id = models.ForeignKey(Group, db_column='group_id', on_delete=models.CASCADE)  # Field name made lowercase.
    is_admin = models.BooleanField(db_column='is_admin')  # Field name made lowercase.


    class Meta:
        managed = True
        unique_together=('user_id','group_id')
        verbose_name_plural='user_groups'
        db_table = 'user_groups'


#stores invitation details for an invited user
class Invitation(models.Model):
    name = models.CharField(max_length=50)#name of invited user
    email = models.EmailField(max_length=200)#email of invited user
    code = models.CharField(max_length=200)#verifies if a user was really invited
    sender = models.ForeignKey(User, on_delete=models.CASCADE)#the sender's email

    def __str__(self):
        return '%s, %s' % (self.sender.username, self.email)

    class Admin:
        pass

    class Meta:
        managed=True
        db_table='invitation'

    def send(self):
        subject = 'Invitation to join Django Bookmarks'

        link = 'http://%s/group_page/accept/%s/' % (
            settings.SITE_HOST,
            self.code
        )
        template = get_template('invitation_email.txt')
        context = {
            'name': self.name,
            'link': link,
            'sender': self.sender.username,
        }
        message = template.render(context)
        send_mail(subject, message,settings.DEFAULT_FROM_EMAIL, [self.email])


class Post(models.Model):
    post_id = models.AutoField(primary_key=True)
    content = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        managed=True
        db_table='post'

    # def __str__(self):
    #     return self.content

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date']
        managed=True
        db_table='comment'

    # def __str__(self):
    #     return 'Comment {} by {}'.format(self.comment, self.username)

class DailyWaterIntake(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    date = models.DateField(blank=False, null=True)  # do we want this to be null?
    cups_of_water = models.IntegerField(null=True,blank=True)

    def add_or_update_water_intake(self,user_id,water_intake):
        DailyWaterIntake.objects.update_or_create(
            # if data for this user already exists in database, update it. Otherwise, create new entry
            user_id=user_id, date=datetime.today(),
            defaults={'cups_of_water': water_intake},  # dictionary for either update or create
        )
    def daily_water_intake(self,user_id):
        water_intake = DailyWaterIntake.objects.filter(user_id=user_id, date=datetime.today()).first()
        return 0 if water_intake is None else water_intake.cups_of_water

    class Meta:
        unique_together = ('user_id', 'date')
        managed = True
        db_table = 'daily_water_intake'
        constraints = [
            models.CheckConstraint(
                check=models.Q(
                    cups_of_water__gte=0  # Translates to calorie_eaten_per_food>=0
                    # see https://docs.djangoproject.com/en/2.2/ref/models/constraints/#django.db.models.CheckConstraint
                ),
                name="cups_of_water_constraint",
            )
        ]

