from http import HTTPStatus
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.core.cache import cache

from posts.models import Post, Group

User = get_user_model()


class PostsURLTests(TestCase):
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
            text='Текстовое поле',
        )

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='HasNoName')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.post.author)
        cache.clear()

    def test_url_exists_at_desired_location_authorized(self):
        addres_status_code = {
            '/create/': HTTPStatus.OK,
            '/follow/': HTTPStatus.OK,
            f'/posts/{self.post.id}/edit/': HTTPStatus.OK
        }
        for address, status_code in addres_status_code.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, status_code)

    def test_create_url_redirect_anonymous_on_login(self):
        response = self.guest_client.get('/create/', follow=True)
        self.assertRedirects(
            response, '/auth/login/?next=/create/'
        )

        response = self.guest_client.get(
            f'/posts/{self.post.id}/edit/',
            follow=True
        )
        self.assertRedirects(
            response, f'/auth/login/?next=/posts/{self.post.id}/edit/'
        )

    def test_url_exists_at_desired_location(self):
        addres_status_code = {
            '/': HTTPStatus.OK,
            f'/posts/{self.post.id}/': HTTPStatus.OK,
            f'/profile/{self.user.username}/': HTTPStatus.OK,
            f'/group/{self.group.slug}/': HTTPStatus.OK,
            '/unexisting_page/': HTTPStatus.NOT_FOUND
        }
        for address, status_code in addres_status_code.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, status_code)

    def test_urls_uses_correct_template(self):
        templates_url_names = {
            '/': 'posts/index.html',
            '/follow/': 'posts/follow.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            f'/profile/{self.user.username}/': 'posts/profile.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            '/create/': 'posts/create_post.html',
            f'/posts/{self.post.id}/edit/': 'posts/create_post.html'
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)
