from datetime import datetime

from django.contrib.auth.models import User
from django.db import transaction
from django.db.utils import IntegrityError
from django.db.models import CheckConstraint
from django.test import TestCase
# from django.db.models import CheckConstraint
from health_tracker.models import DailyWaterIntake,UserFood,FoodDictionary
from django.utils import timezone


class TestModels(TestCase):
    def setUp (self):
        self.water_intake=DailyWaterIntake()
        self.test_user=User.objects.create(password='123',last_login=timezone.now(),is_superuser=False,
                                          username='Hm_20',first_name='Hemal',last_name='Munbodh',email='h@email.com',
                                          is_staff=False,is_active=True,date_joined=timezone.now())
        self.entry=FoodDictionary()
        self.food_name='Omlette Fried Rice with chicken'

    def test_daily_water_intake_has_valid_range(self):
        #tests if daily_water_intake table accepts wrong values
        self.assertRaises(IntegrityError,self.water_intake.add_or_update_water_intake,self.test_user.id,-1) # test for check constraint

    def test_food_dictionary_entry_has_valid_calories_range(self):
        self.assertRaises(IntegrityError, self.entry.save_new_food, food_name=self.food_name, calories=0)

    def test_food_dictionary_entry_has_valid_food_name(self):
        self.assertRaises(IntegrityError,self.entry.save_new_food,food_name=None,calories=30)

    def test_food_dictionary_entry_has_valid_calorie_constraints(self):
        self.assertRaises(IntegrityError,self.entry.save_new_food,food_name=self.food_name,calories=None)











