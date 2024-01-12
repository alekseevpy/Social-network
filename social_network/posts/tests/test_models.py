from django.contrib.auth import get_user_model
from django.test import TestCase

from posts.models import Post, Group

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Текстовое поле длинее 15 символов'
        )

    def test_models_have_correct_object_names(self):
        group = PostModelTest.group
        expected_group__str__ = group.title
        self.assertEqual(expected_group__str__, str(group))

        post = PostModelTest.post
        expected_post__str__ = post.text[:15]
        self.assertEqual(expected_post__str__, str(post))
