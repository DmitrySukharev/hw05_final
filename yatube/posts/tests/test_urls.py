from http import HTTPStatus

from django.core.cache import cache
from django.test import Client, TestCase
from posts.models import Group, Post, User


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание группы',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост, который предназначен для тестов.',
        )
        cls.post_page = f'/posts/{cls.post.id}/'
        cls.post_edit_page = f'/posts/{cls.post.id}/edit/'

    def setUp(self):
        self.guest_client = Client()
        self.another_user = User.objects.create_user(username='another_user')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.another_user)
        self.author_client = Client()     # клиент для автора тестового поста
        self.author_client.force_login(PostURLTests.user)
        cache.clear()

    def test_general_url_access(self):
        """.Проверяем доступность страниц для неавторизованого пользователя."""
        urls_for_tests = {
            '/': HTTPStatus.OK,
            '/group/test-slug/': HTTPStatus.OK,
            '/profile/auth/': HTTPStatus.OK,
            PostURLTests.post_page: HTTPStatus.OK,
            '/unexisting_page/': HTTPStatus.NOT_FOUND,
        }
        for test_url, status_code in urls_for_tests.items():
            with self.subTest(url=test_url):
                response = self.guest_client.get(test_url)
                self.assertEqual(response.status_code, status_code)

    def test_new_post_availability_for_authorized_users(self):
        """.Проверяем доступность страницы /create/ для авторизованного
         пользователя.
        """
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_new_post_redirect_anonymous_to_login(self):
        """.Проверяем редирект по адресу /create/ для неавторизованного
         пользователя на страницу логина.
        """
        response = self.guest_client.get('/create/', follow=True)
        self.assertRedirects(response, '/auth/login/?next=/create/')

    def test_post_editing_redirect_for_non_author(self):
        """.Проверяем редирект на странице редактирования поста для анонимного
         пользователя или для пользователя, отличного от автора.
        """
        clients = {
            'anonymous': self.guest_client,
            'non-author': self.authorized_client
        }
        for client_name, client in clients.items():
            with self.subTest(client=client_name):
                response = client.get(PostURLTests.post_edit_page, follow=True)
                self.assertRedirects(response, PostURLTests.post_page)

    def test_post_editing_for_author(self):
        """.Проверяем доступность страницы редактирования поста для автора."""
        response = self.author_client.get(PostURLTests.post_edit_page)
        self.assertEqual(response.status_code, 200)

    def test_urls_use_correct_templates(self):
        """.Проверяем правильность использования шаблонов для urls."""
        url_templates = {
            '/': 'posts/index.html',
            '/group/test-slug/': 'posts/group_list.html',
            '/profile/auth/': 'posts/profile.html',
            PostURLTests.post_page: 'posts/post_detail.html',
            PostURLTests.post_edit_page: 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
        }
        for address, template in url_templates.items():
            with self.subTest(address=address):
                response = self.author_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_new_comment_redirect_anonymous_to_login(self):
        """.Проверяем редирект при комментировании для неавторизованного
        пользователя на страницу логина.
        """
        test_url = f'/posts/{self.post.id}/comment/'
        data = {'text': 'Тестовый комментарий.'}
        response = self.guest_client.post(test_url, data, follow=True)
        self.assertRedirects(response, '/auth/login/?next=' + test_url)
        self.assertEqual(self.post.comments.count(), 0)
