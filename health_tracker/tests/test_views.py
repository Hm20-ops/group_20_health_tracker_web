from django.test import TestCase, Client
from django.urls import reverse
from health_tracker.models import FoodDictionary,UserFood

class TestViews(TestCase):

    def setUp(self):
        self.client=Client()
        self.diet_url=reverse('diet')
        self.diet_add_new_food_url=reverse('add_new_food')

    def test_diet_renders_GET(self):
        response=self.client.get(self.diet_url)
        self.assertEquals(response.status_code,200)
        self.assertTemplateUsed(response,'diet.html')

    def test_save_new_food_to_dictionary(self):
        response=self.client.post(self.diet_add_new_food_url,{'food_name':'pizza roll','calories_per_100g':100})
        self.assertEquals(response.status_code,200)
        self.assertEquals(FoodDictionary.objects.get(food_name='pizza roll').food_name,'pizza roll')

    def test_save_invalid_food_calorie_to_dictionary(self):
        response=self.client.post(self.diet_add_new_food_url,{'food_name':'pizza roll','calories_per_100g':0})
        self.assertEquals(response.status_code,400,"Invalid base calorific value")

    def test_save_invalid_food_name_to_dictionary(self):
        response=self.client.post(self.diet_add_new_food_url,{'food_name':'','calories_per_100g':0})
        self.assertEquals(response.status_code,400,"Invalid base calorific value")












