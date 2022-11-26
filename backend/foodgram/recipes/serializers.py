from django.shortcuts import get_object_or_404
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from users.models import CustomUser
from users.serializers import CustomUserSerializer

from .models import (
    Favorite,
    Follow,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShopList,
    Tags,
)


class TagsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tags
        fields = "__all__"


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = "__all__"


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(
        source="ingredient.id",
    )
    name = serializers.ReadOnlyField(
        source="ingredient.name",
    )
    measurement_unit = serializers.ReadOnlyField(source="ingredient.measurement_unit")

    class Meta:
        model = RecipeIngredient
        fields = (
            "id",
            "name",
            "measurement_unit",
            "amount",
        )


class CreateIngredientRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Ингредиенты + рецепты."""

    id = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ("id", "amount")


class RecipesCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания объектов Рецепты."""

    author = CustomUserSerializer(read_only=True)
    ingredients = CreateIngredientRecipeSerializer(many=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            "id",
            "tags",
            "author",
            "ingredients",
            "name",
            "image",
            "text",
            "cooking_time",
        )

    # def validate(self, data):
    #     print(data)
    #     ingredients = data["ingredients"]
    #     ingredient_list = []
    #     cook_time = data["cooking_time"]
    #     cook_time_list = []
    #     amount_ingredient = data["amount"]

    #     for items in ingredients:
    #         ingredient = Ingredient.objects.get(id=items["name"])
    #         if ingredient in ingredient_list:
    #             raise serializers.ValidationError("Дублирование ингредиента")
    #         ingredient_list.append(ingredient)
    #         if ingredient_list <= 0:
    #             raise serializers.ValidationError("Ингредиентов меньше 0!")
    #     if cook_time <= 0:
    #         raise serializers.ValidationError(
    #             "Время должно быть неотрицательное!")
    #     cook_time_list.append(cook_time)
    #     if amount_ingredient <= 0:
    #         raise serializers.ValidationError(
    #             "Укажите правильное количество ингедиентов."
    #         )
    #     return data

    def create_ingredients(self, ingredients, recipe):
        create_ingredient = [
            RecipeIngredient(
                recipe=recipe,
                ingredient=get_object_or_404(Ingredient, pk=ingredient["id"]),
                amount=ingredient["amount"],
            )
            for ingredient in ingredients
        ]
        RecipeIngredient.objects.bulk_create(create_ingredient)

    def create(self, validated_data):
        ingredients = validated_data.pop("ingredients")
        tags = validated_data.pop("tags")
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.add(*tags)
        self.create_ingredients(ingredients, recipe)
        return recipe

    def update(self, instance, validated_data):
        instance.ingredients.clear()
        ingredients = validated_data.pop("ingredients")
        tags = validated_data.pop("tags")
        self.create_ingredients(ingredients, instance)
        instance.tags.clear()
        for tag in tags:
            instance.tags.add(tag)
        return super().update(instance, validated_data)


class RecipeSerializer(serializers.ModelSerializer):
    author = CustomUserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        many=True,
        required=True,
        source="ingredients_in_recipe",
    )
    tags = TagsSerializer(many=True)
    image = Base64ImageField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            "id",
            "tags",
            "author",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
            "name",
            "image",
            "text",
            "cooking_time",
        )

    def get_is_favorited(self, obj):
        if self.context["request"].user.is_authenticated:
            current_user = self.context["request"].user
            return Favorite.objects.filter(user=current_user, recipe=obj).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        if self.context["request"].user.is_authenticated:
            current_user = self.context["request"].user
            return ShopList.objects.filter(user=current_user, recipe=obj).exists()
        return False

    def validate(self, data):
        if "request" not in self.context:
            raise serializers.ValidationError("Ошибка запроса")
        return data


class RecipeFollowSerializer(RecipeSerializer):
    """Сериализатор Рецептов для отображения в подписках."""

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")


class FollowSerializer(serializers.ModelSerializer):
    """Создаем сериализатор для просмотра подписок."""

    email = serializers.ReadOnlyField(source="following.email")
    id = serializers.ReadOnlyField(source="following.id")
    username = serializers.ReadOnlyField(source="following.email")
    first_name = serializers.ReadOnlyField(source="following.first_name")
    last_name = serializers.ReadOnlyField(source="following.last_name")

    class Meta:
        fields = (
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
        )
        model = CustomUser


class FollowCreateSerializer(serializers.ModelSerializer):
    """Сериализатор создания объекта Подписки."""

    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all())
    following = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all())
    email = serializers.ReadOnlyField(source="following.email")
    id = serializers.ReadOnlyField(source="following.id")
    username = serializers.ReadOnlyField(source="following.email")
    first_name = serializers.ReadOnlyField(source="following.first_name")
    last_name = serializers.ReadOnlyField(source="following.last_name")
    is_subscribed = serializers.SerializerMethodField(default=True)
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        fields = (
            "user",
            "following",
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
            "recipes",
            "recipes_count",
        )
        model = Follow
        validators = [
            UniqueTogetherValidator(
                queryset=Follow.objects.all(),
                fields=["user", "following"],
                message="Подписка уже есть на этого пользователя.",
            )
        ]

    def get_is_subscribed(self, obj):
        return Follow.objects.filter(user=obj.user, following=obj.following).exists()

    def get_recipes(self, obj):
        request = self.context["request"]
        limit = request.GET.get("recipes_limit")
        queryset = Recipe.objects.filter(author=obj.following)
        if limit:
            queryset = queryset[: int(limit)]
        return RecipeFollowSerializer(queryset, many=True).data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj.following).count()

    def validate(self, data):
        user = data["user"]
        current_follow = data["following"]
        if user == current_follow:
            raise serializers.ValidationError(["Подписка на себя невозможна"])
        return data
